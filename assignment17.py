
# coding: utf-8

# # Homework Assignment 17
# 
# 
# ## Instructions
# 
# Consider the reservoir shown below with the given properties that has been discretized into equal grid blocks.
# 
# ![image](images/grid.png)
# 
# To be clear, there is a constant-rate injector of 1000 ft$^3$/day at $x$ = 5000 ft, $y$ = 5000 ft and a constant BHP well (producer) with $p_w$ = 800 psi at $x$ = 9000 ft, $y$ = 9000 ft. Both wells have a radius of 0.25 ft and no skin factor.
# 
# Use the code you wrote in [Assignment 15](https://github.com/PGE323M-Fall2018/assignment15) and add additional functionality to incorporate the wells.  The wells section of the inputs will look something like:
# 
# ```yml
# 'wells':
#     'rate':
#         'locations': 
#             - [0.0, 1.0]
#             - [9999.0, 2.0]
#         'values': [1000, 1000]
#         'radii': [0.25, 0.25]
#     'bhp':
#         'locations': 
#             - [6250.0, 1.0]
#         'values': [800]
#         'radii': [0.25]
#         'skin factor': 0.0
# ```
# 
# notice that all the values are Python lists so that multiple wells of each type can be included.  The `'locations'` keyword has a value that is a list of lists.  Each sublist contains the $x,y$ Cartesian coordinate pair that gives the location of the well.  You must write some code that can take this $x,y$-pair and return the grid block number that the well resides in.  This should be general enough that changing the number of grids in the $x$ and $y$ directions still gives the correct grid block.  Once you know the grid block numbers for the wells, the changes to `fill_matrices()` should be relatively easy.
# 
# All of the old tests from the last few assignments are still in place, so your code must run in the absence of any well section in your inputs.

# In[2]:


import numpy as np
import scipy.sparse
import scipy.sparse.linalg
import matplotlib.pyplot as plt
import yaml

from assignment13 import OneDimReservoir


# In[11]:


class TwoDimReservoir(OneDimReservoir): 
    #inherits init function from OneDim Reservoir
    
    def parse_inputs(self):
        # had to redefine because input now has Nx, Ny, height, length
        self.viscosity = self.inputs['fluid']['water']['viscosity']
        self.formation_volume_factor = self.inputs['fluid']['water']['formation volume factor']
        self.compressibility = self.inputs['fluid']['water']['compressibility'] 
        
        #grid data
        self.nxgrids = self.inputs['numerical']['number of grids']['x']
        self.nygrids = self.inputs['numerical']['number of grids']['y']
        self.ngrids = self.nxgrids * self.nygrids
        self.delta_t = self.inputs['numerical']['time step']
        
        if 'conversion factor' in self.inputs:
            self.conversion_factor = self.inputs['conversion factor']
        else:
            self.conversion_factor = 1.0
            
        phi = self.inputs['reservoir']['porosity']
        k = self.inputs['reservoir']['permeability']
        d = self.inputs['reservoir']['depth']
        
        self.permeability = self.check_input_and_return_data(k)
        self.depth = self.check_input_and_return_data(d)
        self.porosity = self.check_input_and_return_data(phi)
        
        delta_x = self.assign_delta_x_array()
        delta_y = self.assign_delta_y_array()
        
        self.delta_x, self.delta_y = np.meshgrid(delta_x, delta_y)
        
        self.area = self.delta_x * self.delta_y   
        
        # well data for rate
        if 'wells' in self.inputs:
            if 'rate' in self.inputs['wells']:
                self.rate_well_i = self.compute_well_index_locations('rate')
                self.rate_well_values = np.array(self.inputs['wells']['rate']['values'])
                self.rate_well_j = self.compute_productivity_index('rate')
            else:
                self.rate_well_i = None

            if 'bhp' in self.inputs['wells']:
                self.bhp_well_i = self.compute_well_index_locations('bhp')
                self.bhp_well_values = np.array(self.inputs['wells']['bhp']['values'])
                self.bhp_well_j = self.compute_productivity_index('bhp')
            else:
                self.bhp_well_i = None
        else:
            self.rate_well_i = None
            self.bhp_well_i = None
        
    
    def assign_delta_x_array(self):
        nx = self.nxgrids

        if 'delta x' not in self.inputs['numerical']:
            length = self.inputs['reservoir']['length']
            delta_x = np.float(length) / nx
            delta_x_arr = np.ones(nx) * delta_x
        else:
            delta_x_arr = np.array(self.inputs['numerical']['delta x'])

        return delta_x_arr
    
    def assign_delta_y_array(self):        
        ny = self.nygrids

        if 'delta y' not in self.inputs['numerical']:
            height = self.inputs['reservoir']['height']
            delta_y = np.float(height) / ny
            delta_y_arr = np.ones(ny) * delta_y
        else:
            delta_y_arr = np.array(self.inputs['numerical']['delta y'])

        return delta_y_arr 
    
    def check_input_and_return_data(self, input_name):
            
        if type(input_name) == list or type(input_name) == tuple:
            data = np.array(input_name)

        else:
            ngrids = self.ngrids
            data = (input_name *  np.ones(ngrids))
            
        return data
    
    
    def compute_transmissibility(self, i, j):
        
        mu = self.viscosity
        k = self.permeability
        d = self.depth
        B_alpha = self.formation_volume_factor
        dx = self.delta_x.flatten()
        dy = self.delta_y.flatten()
        
        if k[i] <= 0 and k[j] <= 0:
            transmissibility = 0
        else:
            if abs(i - j) <= 1:
                k_half = k[i] * k[j] * (dx[i] + dx[j]) / (dx[i] * k[j] + dx[j] * k[i])
                dx_half = (dx[i] + dx[j]) / 2
                transmissibility = k_half * d[i] * dy[i] / mu / B_alpha / dx_half 
            else:
                k_half = k[i] * k[j] * (dy[i] + dy[j]) / (dy[i] * k[j] + dy[j] * k[i])
                dx_half = (dy[i] + dy[j]) / 2
                transmissibility = k_half * d[i] * dx[i] / mu / B_alpha / dx_half
                
        return transmissibility
    
    
    def compute_accumulation(self, i):
        
        c_t = self.compressibility
        phi = self.porosity
        B_alpha = self.formation_volume_factor
        
        d = self.depth
        dx = self.delta_x.flatten()
        dy = self.delta_y.flatten()
        
        volume = d[i] * dx[i] * dy[i]
        accumulation = volume * phi[i] * c_t / B_alpha
        
        return accumulation
    

    def compute_well_index_locations(self, well_type):
        dx = self.delta_x
        dy = self.delta_y
        
       #this is the center of the grid
        xc = np.cumsum(dx, axis=1) - dx[:,0,None] / 2.0
        yc = np.cumsum(dy, axis=0) - dy[None, 0,:] / 2.0
        
        #location of the wells
        total_bool_arr = []
        for xl, yl in self.inputs['wells'][well_type]['locations']:
            bool_arr_1 = xc - dx[:,0,None] / 2.0 <= xl
            bool_arr_2 = xc + dx[:,0,None] / 2.0 >  xl
            bool_arr_3 = yc - dy[None,0,:] / 2.0 <= yl 
            bool_arr_4 = yc + dy[None,0,:] / 2.0 >  yl
            total_bool_arr += [np.all([bool_arr_1, bool_arr_2, bool_arr_3, bool_arr_4], axis=0)]
        
        grid_numbers = np.arange(self.ngrids, dtype=np.int).reshape(-1, self.nxgrids)
        
        return grid_numbers[np.any(total_bool_arr, axis = 0)]
    
        
    def compute_productivity_index(self, well_type):
        
        k = self.permeability
        mu = self.viscosity
        dx = self.delta_x.flatten()
        dy = self.delta_y.flatten()
        d = self.depth.flatten()
        factor = self.conversion_factor
        B_alpha = self.formation_volume_factor
        
        if 'skin factor' in self.inputs['wells'][well_type]:
            skin_factor = self.inputs['wells'][well_type]['skin factor']
        else:
            skin_factor = 0.0

        if well_type == 'rate':
            i_well = self.rate_well_i #index of rate wells
        elif well_type == 'bhp':
            i_well = self.bhp_well_i #index of bhp wells
        
        r_w = np.array(self.inputs['wells'][well_type]['radii'])
        
        r_eq = 0.14 * np.sqrt(dx[i_well] ** 2.0 + dy[i_well] ** 2.0) #use peaceman correction to get r_eq

        J = (2.0 * np.pi * k[i_well] * d[i_well]) /  (mu * B_alpha * np.log(r_eq / r_w) + skin_factor) #compute J
        
        return J
    
    
    def fill_matrices(self):
                
        N = self.ngrids
        Nx = self.nxgrids
        Ny = self.nygrids
        factor = self.conversion_factor

        T = scipy.sparse.lil_matrix((N, N))
        B = np.zeros(N)
        Q = np.zeros(N)

        bcs = self.inputs['boundary conditions']
        bc_type_1 = bcs['left']['type']
        bc_type_2 = bcs['right']['type']
        bc_type_3 = bcs['top']['type']
        bc_type_4 = bcs['bottom']['type']
        bc_value_1 = bcs['left']['value']
        bc_value_2 = bcs['right']['value']
        bc_value_3 = bcs['top']['value']
        bc_value_4 = bcs['bottom']['value']
      

        for i in range(N):
            
            if Nx > 1:
                # left BC
                if i % Nx == 0:
                    T[i, i + 1] = -self.compute_transmissibility(i, i + 1)

                    if bc_type_1 == 'prescribed flux':
                        T[i, i] += 0
                    elif bc_type_1 == 'prescribed pressure':
                        T0 = self.compute_transmissibility(i, i)
                        T[i, i] -= 2 * T0
                        Q[i] = 2 * T0 * bc_value_1 * factor
                    else:
                        pass

                #right conditions
                elif (i+1) % Nx == 0:
                    T[i, i - 1] = -self.compute_transmissibility(i, i - 1)

                    if bc_type_2 == 'prescribed flux':
                        T[i, i] += 0
                    elif bc_type_2 == 'prescribed pressure':
                        T0 = self.compute_transmissibility(i, i)
                        T[i, i] -= 2 * T0
                        Q[i] = 2 * T0 * bc_value_2 * factor
                    else:
                        pass
                else:
                    T[i, i + 1] = -self.compute_transmissibility(i, i + 1)
                    T[i, i - 1] = -self.compute_transmissibility(i, i - 1)
            #2d case        
            if Ny > 1: 
                #up condiition
                if i > (N-1) - Nx:

                    T[i, i - Nx] = -self.compute_transmissibility(i, i - Nx)

                    if bc_type_3 == 'prescribed flux':
                        T[i, i] += 0
                    elif bc_type_3 == 'prescribed pressure':
                        T0 = self.compute_transmissibility(i, i)
                        T[i, i] -= 2 * T0
                        Q[i] = 2 * T0 * bc_value_3 * factor
                    else:
                        pass
                       
                # down  condition
                elif i < Nx:
                    T[i, i + Nx] = -self.compute_transmissibility(i, i + Nx)

                    if bc_type_4 == 'prescribed flux':
                        T[i, i] += 0
                    elif bc_type_4 == 'prescribed pressure':
                        T0 = self.compute_transmissibility(i, i)
                        T[i, i] -= 2 * T0
                        Q[i] = 2 * T0 * bc_value_4 * factor
                    else:
                else:
                    T[i, i - Nx] = -self.compute_transmissibility(i, i - Nx)
                    T[i, i + Nx] = -self.compute_transmissibility(i, i + Nx)
                    
            T[i, i] = -np.sum(T[i]) # fill diagonals of T 
            
            B[i] = self.compute_accumulation(i)
            
        #adding the well data to my grid    
        if self.rate_well_i is not None:
            Q[self.rate_well_i] += self.rate_well_values
        if self.bhp_well_i is not None:
            Q[self.bhp_well_i] += self.bhp_well_j * self.bhp_well_values * factor
            T[self.bhp_well_i, self.bhp_well_i] += self.bhp_well_j 
        
        #takinga davantage of sparce matrixes
        self.T = T.tocsr() * factor
        self.B = scipy.sparse.csr_matrix((B, (np.arange(N), np.arange(N))), shape=(N,N))
        self.Q = Q
        
        return
    
    
    def apply_initial_conditions(self):
        '''
            Applies initial pressures to self.p
        '''

        N = self.ngrids

        self.p = np.ones(N) * self.inputs['initial conditions']['pressure']

        return

