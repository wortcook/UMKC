library(ISLR2)
library(MASS)
library(ggplot2)
library(reshape2)
library(e1071)

#data <- data_clean
data <- synthetic_data_25
data <- data[,!names(data) =='X']

data$diagnosis_binary <- ifelse(data$diagnosis=='M',1,0)
data_cor <- data[,!names(data) %in% c('diagnosis','X')]

mlog_model <- glm(
  data$diagnosis_binary ~ data$perimeter_mean + data$compactness_mean + data$concavity_worst + data$texture_se + data$texture_worst + data$area_worst + data$symmetry_worst,
  data = data,
  family=binomial)

summary(mlog_model)

mbayes_model = naiveBayes(
  data$diagnosis_binary ~ data$perimeter_mean + data$compactness_mean + data$concavity_worst + data$texture_se + data$texture_worst + data$area_worst + data$symmetry_worst,
  data = data
)
mbayes_model



#cors <- cor(data_cor)
#print(cors[,31])

#melted_cors <- melt(cors)

#ggplot(data=melted_cors, aes(x=Var1, y=Var2,fill=value)) + geom_tile()


#head(data)

doLogistic <- function(Y,X,data,xlabel){
  log_model <- glm(Y ~ X, data=data, family=binomial)

  Predicted_data <- data.frame(X = seq(min(X), max(X), len=nrow(data)))

  # Fill predicted values using regression model
  Predicted_data$var1 = predict(log_model, Predicted_data, type="response")

# Plot Predicted data and original data points
  plot(y=Y, x=X, xlab=xlabel)
  lines(Predicted_data$var1 ~ Predicted_data$X, Predicted_data, lwd=1, col="green")
  
  log_model.Predicted_data <- Predicted_data
  
  return(log_model)
}

doLDA <- function(Y,X,data){
  lda_model <- lda(Y ~ X,data=data)
  
  print("Predicting")
  # Fill predicted values using regression model
  predictions = predict(lda_model, data , type="response")

  #print(predictions)
    
  #print("Plotting")
  # Plot Predicted data and original data points
  #plot(y=Y, x=X)
  #lines(predictions ~ X, data, lwd=1, col="blue")
  
  return(lda_model)
}

#perimeter_mean
#compactness_mean
#concavity_worst
#texture_se
#texture_worst
#area_worst
#symmetry_worst

#mlogRes =
#doLogistic(data$diagnosis_binary, 
#           data$perimeter_mean + data$compactness_mean + data$concavity_worst + data$texture_se + data$texture_worst + data$area_worst + data$symmetry_worst,
#           data,
#           'multi')




#print(mlogRes)
#for( i in 4:ncol(data)){
#for( i in 3:ncol(data)){
#  print('#################')
#  print(colnames(data)[i])
#  #print("***** Logistic")
#  #print(doLogistic(data$diagnosis_binary,data[,i],data,colnames(data)[i]))
#  #doLogistic(data$diagnosis_binary,data[,i],data,colnames(data)[i])
#  print("***** LDA")
#  lda_res = doLDA(data$diagnosis_binary,data[,i],data)
#  plot(lda_res)
#}



                           