

#data <- `data_clean`
data <- synthetic_data_25

data$diagnosis_binary <- ifelse(data$diagnosis=='M',1,0)

doLogistic <- function(Y,X,data,xlabel){
  log_model_concavity <- glm(Y ~ X, data=data, family=binomial)

  Predicted_data <- data.frame(X = seq(min(X), max(X), len=nrow(data)))

# Fill predicted values using regression model
Predicted_data$var1 = predict(log_model_concavity, Predicted_data, type="response")

# Plot Predicted data and original data points
  plot(y=Y, x=X, xlab=xlabel)
  lines(Predicted_data$var1 ~ Predicted_data$X, Predicted_data, lwd=1, col="green")
}

for( i in 2:ncol(data)){
  doLogistic(data$diagnosis_binary,data[,i],data,colnames(data)[i])
}



                           