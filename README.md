# mixed-panel-logit-default-risk
I use a mixed panel logit model with randomized coefficients across countries and select year-fixed effects using L2 supervised regularization to predict unconditional probabilities of sovereign external debt default for out-of-sample years. 

For future research, I wish to combine predicted probabilities with estimated "haircut" data to generate a risk score which is interpreted as the unconditional rate of foreign investment loss resulting from default. 

Last Updated: 9/30/19

### Dependencies
[pylogit](https://github.com/timothyb0912/pylogit)
