#From Wisconsin Breast Cancer Data - Synthetic set #25

#plot(y=factor(synthetic_data_25$diagnosis), x=synthetic_data_25$radius_mean)

#print("Correlation Matrix")
#cor_matrix = cor(synthetic_data_25[-c(1)])
#print(cor_matrix)


synthetic_data_25$diagnosis_binary <- ifelse(synthetic_data_25$diagnosis=='M',1,0)

log_model_concavity <- glm(diagnosis_binary ~ radius_mean, data=synthetic_data_25, family=binomial)

Predicted_data <- data.frame(radius_mean = synthetic_data_25$radius_mean)

print(nrow(synthetic_data_25))
print(nrow(Predicted_data))

# Fill predicted values using regression model
Predicted_data$var1 = predict(
  log_model_concavity, Predicted_data, type="response")

# Plot Predicted data and original data points
plot(y=synthetic_data_25$diagnosis_binary, x=synthetic_data_25$radius_mean)
lines(Predicted_data$var1 ~ Predicted_data$radius_mean, Predicted_data, lwd=1, col="green")                           



                           