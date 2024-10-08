library(ISLR2)
library(MASS)
library(ggplot2)
library(reshape2)
library(e1071)
library(utils)
library(ggplot2)

data <- read.csv('./Workspace/UMKC/Fall2024/CS5565-0007/classlab/synthetic_data_25.csv')
plot(data)

#Create a numeric column based on M or B as 0/1
data$diagnosis_binary <- ifelse(data$diagnosis=='B',1,0)
data_cor <- data[,!names(data) %in% c('diagnosis')]
print(summary(data_cor))

cors <- cor(data_cor)
print(cors[,31])

doLogistic <- function(Y,X,data,ylabel,xlabel){
  log_model <- glm(Y ~ X, data=data, family=binomial)
  
  Predicted_data <- data.frame(X = seq(min(X), max(X), len=nrow(data)))
  
  # Fill predicted values using regression model
  Predicted_data$var1 = predict(log_model, Predicted_data, type="response")
  
  # Plot Predicted data and original data points
  plot(y=Y, x=X, xlab=xlabel, ylab=ylabel)
  lines(Predicted_data$var1 ~ Predicted_data$X, Predicted_data, lwd=1, col="green")
  
  return(log_model)
}

doLogistic(data$diagnosis_binary, data$perimeter_mean, data, 'Diagnosis (B==1)', 'Perimeter mean' )
doLogistic(data$diagnosis_binary, data$compactness_mean, data, 'Diagnosis (B==1)', 'Compactnessmean' )
doLogistic(data$diagnosis_binary, data$concavity_worst, data, 'Diagnosis (B==1)', 'Concavity worst' )
doLogistic(data$diagnosis_binary, data$texture_se, data, 'Diagnosis (B==1)', 'Texture se' )
doLogistic(data$diagnosis_binary, data$texture_worst, data, 'Diagnosis (B==1)', 'Texture worst' )
doLogistic(data$diagnosis_binary, data$area_worst, data, 'Diagnosis (B==1)', 'Area worst' )
doLogistic(data$diagnosis_binary, data$symmetry_worst, data, 'Diagnosis (B==1)', 'Symmetry worst' )

#split data into train and test
#From https://www.statology.org/train-test-split-r/
set.seed(5)
sample <- sample(c(TRUE,FALSE), nrow(data), replace=TRUE, prob=c(0.8, 0.2))
data_train <- data[sample,]
data_test  <- data[!sample,]

print(nrow(data_train))
print(nrow(data_test))

mlog_model <- glm(
  diagnosis_binary ~ perimeter_mean + compactness_mean + concavity_worst + texture_se + texture_worst + area_worst + symmetry_worst,
  data = data_train,
  family=binomial)

summary(mlog_model)

data_test$probs <- predict(mlog_model, newdata = data_test, type="response")
data_test$pred <- rep('B',nrow(data_test))
data_test$pred[data_test$probs < 0.5] = 'M'
test_actual = data_test$diagnosis
test_prediction = data_test$pred

table(test_actual, test_prediction)

lda_model = lda(
  diagnosis ~ fractal_dimension_se+perimeter_mean + compactness_mean + concavity_worst + texture_se + texture_worst + area_worst + symmetry_worst,
  data = data_train
)

plot(lda_model)

lda_pred <- predict(lda_model, newdata = data_test)
names(lda_pred)
lda_class <- lda_pred$class
table(test_actual,lda_class)

bayes_model <- naiveBayes(
  diagnosis ~ perimeter_mean + compactness_mean + concavity_worst + texture_se + texture_worst + area_worst + symmetry_worst,
  data = data_train
)

print(bayes_model)
bayes_class <- predict(bayes_model, data_test)
table(test_actual,bayes_class)
