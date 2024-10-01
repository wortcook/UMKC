library(ISLR2)
library(MASS)

#data <- `data_clean`
data <- synthetic_data_25

data$diagnosis_binary <- ifelse(data$diagnosis=='M',1,0)

doLogistic <- function(Y,X,data,xlabel){
  log_model <- glm(Y ~ X, data=data, family=binomial)

  log_model.Predicted_data <- data.frame(X = seq(min(X), max(X), len=nrow(data)))

  # Fill predicted values using regression model
  Predicted_data$var1 = predict(log_model, Predicted_data, type="response")

# Plot Predicted data and original data points
#  plot(y=Y, x=X, xlab=xlabel)
#  lines(Predicted_data$var1 ~ Predicted_data$X, Predicted_data, lwd=1, col="green")
  
  return(log_model)
}

doLDA <- function(Y,X,data){
  head(X)
  lda_model <- lda(Y ~ X,data=data)
  return(lda_model)
}

for( i in 2:ncol(data)){
  print('#################')
  print(colnames(data)[i])
  print("***** Logistic")
  print(doLogistic(data$diagnosis_binary,data[,i],data,colnames(data)[i]))
  print("***** LDA")
  lda_res = doLDA(data$diagnosis_binary,data[,i],data)
  plot(lda_res)
  
}



                           