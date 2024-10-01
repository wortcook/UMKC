

data <- `data_clean`
#data <- synthetic_data_25

data$diagnosis_binary <- ifelse(data$diagnosis=='M',1,0)

log_model_concavity <- glm(diagnosis_binary ~ radius_mean, data=data, family=binomial)

Predicted_data <- data.frame(radius_mean = seq(min(data$radius_mean), max(data$radius_mean), len=nrow(data)))

print(nrow(synthetic_data_25))
print(nrow(Predicted_data))

# Fill predicted values using regression model
Predicted_data$var1 = predict(log_model_concavity, Predicted_data, type="response")

# Plot Predicted data and original data points
plot(y=data$diagnosis_binary, x=data$radius_mean)
lines(Predicted_data$var1 ~ Predicted_data$radius_mean, Predicted_data, lwd=1, col="green")                           



                           