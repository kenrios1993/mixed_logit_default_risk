# -*- coding: utf-8 -*-
"""
Created on Thu Nov 29 23:48:25 2018

Author: Kenneth Rios
Last Updated: 12/18/2018
"""

import matplotlib.pylab as plt
import pylogit  # must download source files @ https://github.com/timothyb0912/pylogit
import numpy as np
import pandas as pd
import sklearn.metrics as sklm

from collections import OrderedDict 

# Import data
train = pd.read_csv("C:\\Users\\kenri\\Data_Bootcamp\\Research Project\\Python\\Output\\mixed_panel_data.csv")

# Generate year dummies for each year present in the data
year_dummies = pd.get_dummies(train["Year"]).rename(columns = lambda x: 'year' + str(x))
train = pd.concat([train, year_dummies], axis=1)


# Subset training and tests datasets according to cutoff year
test = train.loc[train.Year >= 2010]          # Post-2009
train = train[~train.index.isin(test.index)]  # Pre-2010


# Initialize ordered dictionaries
basic_specification = OrderedDict()
basic_names = OrderedDict()


# Model year-fixed effects (include only recession years in order to ensure convergence!)
#for year in year_dummies.columns.tolist():
#    basic_specification[year] = [["Default"]]
#    basic_names[year] = ["Year " + year[-4:]]

basic_specification["year2001"] = [["Default"]]
basic_names["year2001"] = ["Year 2001"]

basic_specification["year2007"] = [["Default"]]
basic_names["year2007"] = ["Year 2007"]

basic_specification["year2008"] = [["Default"]]
basic_names["year2008"] = ["Year 2008"]

basic_specification["year2009"] = [["Default"]]
basic_names["year2009"] = ["Year 2009"]

    
# Model coefficients randomized over countries
vars = {"Netforeignassets_currentLCU" : "Net Foreign Assets (current LCU)",
        "Inflationconsumerprices_annualpc" : "Inflation (annual % change in CPI)",
        "Externalbalanceongoodsandservice" : "External Trade Balance (% of GDP)",
        "Currentaccountbalance_BoPcurrent" : "Current Account Balance (current USD)",
        "Nettradeingoodsandservices_BoPcu" : "Balance of Payments (current USD)",
        "Unemploymenttotal_pctoftotallabo" : "Unemployment (% of labor force)",
        "DGDP" : "Real GDP Growth (YOY % change)",
        "RYPC" : "Real GDP per capita growth (annual % change)",
        "CGEB" : "Change in Net Exports (% of GDP)",
        "PSBR" : "Central Government Balance (% of GDP)",
        "BINT" : "Interest Payments on Government Debt (% of GDP)",
        "PUDP" : "Total Debt owed by Government to Domestic and Foreign Creditors (% of GDP)",
        "SODD" : "Bank Lending to Public and Private Sectors (annual % change)",
        "CARA" : "Current Account Balance (% of GDP)",
        "IRTD" : "Total International Reserves (% of external debt stock)",
        "TDPX" : "Total External Debt Stock (% of exports)",
        "TDPY" : "Total External Debt (% of GDP)",
        "TSPY" : "Total External Debt Service Paid (% of GDP)",
        "INPS" : "Total Interest Payments made on External Debt (% of total debt service paid)",
        "INPY" : "Total Interest Payments made on External Debt (% of GDP)",
        "XRRE" : "Real Effective Exchange Rate (weighted by trade)"}

for key in vars:
    basic_specification[key] = [["Default"]]
    basic_names[key] = [vars[key]]

# Store variables whose coefficients are to be randomized over countries
index_var_names = list(vars.values())
    




##### 10-FOLD CROSS-VALIDATION #####
print("\n##### 10-FOLD CROSS-VALIDATION #####\n")

# Initialize lambda dictionary
lambdas = {}

# Shuffle training set
train = train.sample(frac = 1, random_state = 3)

# Generate a list of 10 cutoff indices that (roughly) equally divide the training data
indices = [0, 52, 104, 156, 208, 260, 312, 364, 416, 468, 526]

# Perform 10-fold cross-validation (Takes FOREVER to run... >24 hours)
for i in np.arange(0, 101, 1):
    
    NLL = 0
    
    for k in range(len(indices)-1):

        # For each fold k, create the holdout set and the bagged set
        holdout = train.iloc[indices[k]:indices[k+1], :].sort_values(by = ["Year", "Country"])
        bagged = train[~train.index.isin(holdout.index)].sort_values(by = ["Year", "Country"])
    
        # Create mixed logit model with year fixed-effects and random coefficients over countries
        model = pylogit.create_choice_model(data = bagged,
                                            alt_id_col = "Status",
                                            obs_id_col = "Year",
                                            choice_col = "default_RR",   # =1 for default, =0 for no default
                                            specification= basic_specification,
                                            model_type = "Mixed Logit",  # mixed panel logit model
                                            names = basic_names,
                                            mixing_id_col = "Country",   # implies coefficients randomized over countries
                                            mixing_vars = index_var_names)
        
        
        # Estimate mixed logit model using Nelder-Mead algorithm (cross-validated to choose optimal lambda) on K-1 folds
        model.fit_mle(init_vals = np.zeros(46),
                      num_draws = 1000,  # 1000 draws from independent normal distributions for each parameter,
                      #seed = 2,         # as functions of their means and standard deviations
                      method = "Nelder-Mead",  # using Nelder-Mead algorithm
                      maxiter = 10,  # number of Nelder-Mead iterations
                      ridge = i)     # ridge = penalty term 'i' on the sum of squares of estimated parameters
        
        
        # Forecast unconditional probabilities using panel_predict() on the kth fold
        probs = model.panel_predict(holdout,
                                    #seed = 2
                                    num_draws = 1000)  # use 1000 draws from the estimated independent  
                                                       # normal distribution for each randomized coefficient
        
        
        # Calculate negative log-likelihood, which is the cross-validation error of the kth fold
        observed_values = holdout["default_RR"].values
        log_predicted_probs = np.log(probs)
        
        negative_log_likelihood = -1 * observed_values.dot(log_predicted_probs)
        NLL += negative_log_likelihood
    
        print("\n")
        print("ESTIMATION FOR FOLD " + str(k+1) + " USING LAMBDA = " + str(i) + " CONVERGED")
        print("\n")
    
    # Calculate CV negative log-likelihood for given lambda and store in lambdas dictionary
    CV_NLL = NLL / 10
    print("THE CROSS-VALIDATION ERROR FOR LAMBDA = " + str(i) + " IS " + str(CV_NLL))
    print("\n")
    
    lambdas[i] = CV_NLL
        
# Return lambda which corresponds to the -lowest- CV negative log-likelihood
lambda_CV = sorted(lambdas, key = lambdas.get)[0]





##### PREDICTION #####
print("\n##### OUT-OF-SAMPLE PREDICTION #####\n")

# Fit the mixed panel logit model on the entire training dataset using the optimal lambda_CV
train = train.sort_values(by = ["Year", "Country"])
      
model = pylogit.create_choice_model(data = train,
                                    alt_id_col = "Status",
                                    obs_id_col = "Year",
                                    choice_col = "default_RR",   
                                    specification= basic_specification,
                                    model_type = "Mixed Logit",  
                                    names = basic_names,
                                    mixing_id_col = "Country",  
                                    mixing_vars = index_var_names)

model.fit_mle(init_vals = np.zeros(46),
              num_draws = 1000,
              #seed = 100,         
              method = "Nelder-Mead",
              maxiter = 1000,  
              ridge = lambda_CV)

# Output regression table
print(model.get_statsmodels_summary())

# Predict unconditional probabilities on the test set using the fully calibrated model
test["probs"] = model.panel_predict(test,
                                    #seed = 101,
                                    num_draws = 1000)





##### ROC CURVE ANALYSIS #####
# Initial false-positive and true-positive rates as dictionaries
fpr = dict()
tpr = dict()

roc_auc = dict()
for i in range(2):
    fpr[i], tpr[i], _ = sklm.roc_curve(test["default_RR"], test["probs"])
    roc_auc[i] = sklm.auc(fpr[i], tpr[i])

# Display AUC statistic and calculate accuracy ratio
AUC = sklm.roc_auc_score(test["default_RR"], test["probs"])
AR = (AUC - .5) / .5

print("AUC = " + str(AUC))
print("AR = " + str(AR))

# Plot ROC curve
plt.figure()
plt.plot(fpr[1], tpr[1])
plt.plot([0, 1], [0, 1], color = 'black', lw = 1, linestyle = '-')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC of Mixed Panel Logit')
plt.show()

# Save prediction data 
test.to_excel("C:\\Users\\kenri\\Data_Bootcamp\\Research Project\\Python\\Output\\test.xlsx", index = False)
                          
