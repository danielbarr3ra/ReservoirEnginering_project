
# coding: utf-8

# # Project 2
# 
# 
# ## Instructions
# 
# In this project, you will solve a two-dimensional reservoir simulation in a heterogenuous reservoir with multple wells.  Essentially, all of the functionality needed to do this was already implemented in [Homework Assignment 17](https://github.com/PGE323M-Fall2017/assignment17).  We will use real data from the Nechelik reservoir that we have looked at several times throughout the semester.
# 
# For this project, you should implement the class below `Project2()` which inherits from `TwoDimReservoir` (which inherits from `OneDimReservoir`).  You may need to import these two base classes from the last assignments you used them ([Homework Assignment 13](https://github.com/PGE323M-Fall2018/assignment13) and [Homework Assignment 17](https://github.com/PGE323M-Fall2018/assignment17) in most cases) by converting those Jupyter Notebooks to Python files and placing the Python files in this repository.
# 
# You will need to implement some functionality to read the porosity and permeability information from a file.  You will notice in [input.yml](input.yml), that these values take the filenames [`Nechelik_perm.dat`](Nechelik_perm.dat) and [`Neckelik_poro.dat`](Nechelik_poro.dat).  These files have the permeability and porosity data, respectively, for each grid block.
#  
# Other than reading the data from a file, you may not need to write any additional code for your simulation to work.  However, it might be a good idea to write a few plotting routines to produce some plots like this one
# 
# ![img](images/contour.png)
# 
# to help you determine if your code is working correctly.
# 
# ## Testing
# 
# There are no locally available tests for this project, but if your `TwoDimReservoir` class passed all tests from [Homework Assignment 17](https://github.com/PGE323M-Fall2017/assignment17) you can be reasonably assured it will work correctly.  Tests will be run on Travis and you will recieve feedback on whether they are passing or not upon submission. You can continue to resubmit until the deadline.
# 
# I encourage you to come up with your own tests as well.  One thing you can do is to work the project in CMG, which I have recorded a tutorial for [here](https://youtu.be/0wFy36pjdX8).  The tutorial covers the exact set of inputs shown in the [inputs.yml](inputs.yml) file and are summarized below.  The pressures in each grid block from your code should agree with CMG within 0.1 psi.
# 
# As you know, the actual Nechelik field has an irregular geometry as shown in the figure, with maximum $d = 100$ ft, $h = 5753$ ft and maximum $L = 7060.5$ ft. There are $N = 1188$ values in the data files corresponding to $N_x$ = 54 and $N_y$ = 22 grids to be used in the reservoir.  The reservoir has constant properties $\mu = 1$ cp, $B_\alpha = 1$, $c_t = 1 \times 10^{-6}$ psi$^{-1}$ and an inital reservoir pressure of $p_{\mbox{initial}} = 3700$ psi.
# 
# The reservoir has the following wells
# 
# |**Well**|**Location**<br> (ft, ft)|**Well type** | **Operating conditions** <br> (ft$^3$/day or psi)|
# |:-:|:-:|:-:|:-:|
# |1| 5536, 3500| Constant BHP | 2000 |
# |2| 5474, 4708| Constant BHP | 2000 |
# |3| 3600, 4937| Constant BHP | 2000 |
# |4| 2400, 3322| Constant BHP | 2000 |
# |5| 2500, 4050| Constant rate injector | 1000 |
# 
# All wells have a radius of $r_w = 0.25$ ft and negligible skin factor.

# In[1]:


import numpy as np
import scipy.sparse
import scipy.sparse.linalg
import matplotlib.pyplot as plt
import yaml
from assignment17 import TwoDimReservoir


# In[2]:


class Project2(TwoDimReservoir):      
            
    def __init__(self, inputs):
        
        super().__init__(inputs)

