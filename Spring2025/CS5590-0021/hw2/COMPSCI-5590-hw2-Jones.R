speed_data <- read.csv("/Users/thomasjones/workspace/UMKC/Spring2025/CS5590-0021/hw2/speed.data.csv")

# Load necessary libraries
library(ggplot2)
library(tidyr)

############################
# 1
# Generate boxplots for vehicular before and after speeds data. Discuss and compare the results. 
############################
# Assuming your data is in a data frame called 'speed_data'
# If not, you can create it like this:
# speed_data <- data.frame(speed_before = c(...), speed_after = c(...))

# Reshape data for better visualization (long format)
speed_data_long <- pivot_longer(speed_data, 
                                cols = c("speed_before", "speed_after"),
                                names_to = "period", 
                                values_to = "speed")

# Create boxplot
ggplot(speed_data_long, aes(x = period, y = speed, fill = period)) +
  geom_boxplot() +
  labs(title = "Comparison of Vehicle Speeds Before and After Legislative Changes",
       x = "Period",
       y = "Speed (units)") +
  scale_fill_manual(values = c("speed_before" = "lightblue", "speed_after" = "lightgreen")) +
  theme_minimal()

# Add some basic statistics
before_stats <- summary(speed_data$speed_before)
after_stats <- summary(speed_data$speed_after)

cat("\nSpeed Before Legislative Changes:\n")
print(before_stats)

cat("\nSpeed After Legislative Changes:\n")
print(after_stats)

# Perform paired t-test to check for significant difference
t_test_result <- t.test(speed_data$speed_before, speed_data$speed_after, paired = TRUE)
cat("\nPaired t-test results:\n")
print(t_test_result)

############################
# 2
# Generate 99% confidence intervals for mean vehicular before-speed data, assuming the population
# variance is unknown. Explain each step and interpret the results. 
############################
# Calculate 99% CI for speed_before (unknown population variance)
speed_before <- speed_data$speed_before
n <- length(speed_before)
sample_mean <- mean(speed_before)
sample_sd <- sd(speed_before)
standard_error <- sample_sd / sqrt(n)

# Critical t-value (two-tailed)
t_critical <- qt(0.995, df = n - 1)  # 0.995 because 1 - (1-0.99)/2

# Calculate confidence interval
ci_lower <- sample_mean - t_critical * standard_error
ci_upper <- sample_mean + t_critical * standard_error

# Print results
cat("99% Confidence Interval for Mean Before-Speed:\n")
cat(sprintf("Lower bound: %.2f\nUpper bound: %.2f\n", ci_lower, ci_upper))
cat(sprintf("Sample mean: %.2f\nMargin of error: ±%.2f\n", 
            sample_mean, t_critical * standard_error))

t.test(speed_before, conf.level = 0.99)$conf.int

############################
# 3
# Generate 90% confidence intervals for the variance of after-speed data. Explain each step and interpret
# the results.
############################
# Extract after-speed data
speed_after <- speed_data$speed_after
n <- length(speed_after)
sample_var <- var(speed_after)  # Sample variance (s²)

# Chi-squared critical values (for 90% CI)
alpha <- 0.10
chi_sq_lower <- qchisq(1 - alpha/2, df = n - 1)
chi_sq_upper <- qchisq(alpha/2, df = n - 1)

# Calculate CI for variance
ci_lower_var <- ((n - 1) * sample_var) / chi_sq_lower
ci_upper_var <- ((n - 1) * sample_var) / chi_sq_upper

# Print results
cat("90% Confidence Interval for After-Speed Variance:\n")
cat(sprintf("Lower bound: %.2f\nUpper bound: %.2f\n", ci_lower_var, ci_upper_var))
cat(sprintf("Sample variance (s²): %.2f\n", sample_var))

###############################
# 4
# Test whether the mean speed is equal to 65 mph after repealing the speed limit at the α=1%
# significance level. Write each step of the hypotheses test and interpret the results. 
###############################
speed_after <- speed_data$speed_after
n <- length(speed_after)
sample_mean <- mean(speed_after)
sample_sd <- sd(speed_after)
mu0 <- 65

t_stat <- (sample_mean - mu0) / (sample_sd / sqrt(n))
cat("t-test statistic:", t_stat, "\n")

##############################
# 5
# Test whether the variance of after-speed data is less than 18 mph at the α=5% significance level. Write
# each step of the hypotheses test and interpret the results. 
#############################
# Load data
speed_after <- speed_data$speed_after
n <- length(speed_after)
cat("Length of speed_after",n)
speed_after <- speed_data$speed_after[!is.na(speed_data$speed_after)]
sigma0_squared <- 18
sample_var = var(speed_after)
cat("Sample Var", sample_var)

# Test statistic
chi_sq_stat <- (n - 1) * sample_var / sigma0_squared

# Critical value (left-tailed)
alpha <- 0.05
chi_sq_critical <- qchisq(alpha, df = n - 1)

# p-value
p_value <- pchisq(chi_sq_stat, df = n - 1)

# Results
cat("--- Variance Hypothesis Test ---\n")
cat("Sample variance (s²):", sample_var, "\n")
cat("Chi-squared statistic:", chi_sq_stat, "\n")
cat("Critical value (α=0.05):", chi_sq_critical, "\n")
cat("p-value:", p_value, "\n")

# Decision
if (chi_sq_stat < chi_sq_critical) {
  cat("Conclusion: Reject H₀. Variance is LESS than 18 mph².\n")
} else {
  cat("Conclusion: Fail to reject H₀. No evidence variance < 18 mph².\n")
}

#############################
# 6
# Test that the vehicular before-speed variance is less than after-speed at the α=10% significance level.
# Write each step of the hypotheses test and interpret the results.
#############################
# Step 1: Data Prep
speed_before <- speed_data$speed_before
speed_after <- speed_data$speed_after[!is.na(speed_data$speed_after)]

# Step 2: Compute Variances and F-statistic
var_before <- var(speed_before)
var_after <- var(speed_after)
f_stat <- var_before / var_after

# Step 3: Critical Value (Left-tailed)
alpha <- 0.10
df_before <- length(speed_before) - 1
df_after <- length(speed_after) - 1
f_critical <- qf(alpha, df1 = df_before, df2 = df_after)

# Step 4: p-value
p_value <- pf(f_stat, df1 = df_before, df2 = df_after)

# Results
cat("--- F-Test for Variance Comparison (Before < After) ---\n")
cat("Sample variance (before):", var_before, "\n")
cat("Sample variance (after):", var_after, "\n")
cat("F-statistic:", f_stat, "\n")
cat("Critical F-value (α=0.10):", f_critical, "\n")
cat("p-value:", p_value, "\n")

# Decision
if (f_stat < f_critical) {
  cat("Conclusion: Reject H₀. Before-speed variance is SMALLER (α=0.10).\n")
} else {
  cat("Conclusion: Fail to reject H₀. No evidence before variance < after.\n")
}

#################################
# 7
# Test that the vehicular after-speed mean is greater than before-speed at the α=5% significance level.
# Write each step of the hypotheses test and interpret the results. 
#################################
# Step 1: Data Prep
speed_before <- speed_data$speed_before
speed_after <- speed_data$speed_after[!is.na(speed_data$speed_after)]

# Step 2: Check Normality
shapiro_before <- shapiro.test(speed_before)
shapiro_after <- shapiro.test(speed_after)
if (shapiro_before$p.value < 0.05 | shapiro_after$p.value < 0.05) {
  warning("Data may not be normal; consider Mann-Whitney U test.")
}

# Step 3: Check Equal Variance
var_test <- var.test(speed_before, speed_after)
equal_var <- var_test$p.value > 0.05

# Step 4: Run t-test
t_test_result <- t.test(speed_after, speed_before,
                        alternative = "greater",
                        var.equal = equal_var)

# Step 5: Results
cat("--- t-Test for Mean Comparison (After > Before) ---\n")
cat("Sample means:\nBefore:", mean(speed_before), "\nAfter:", mean(speed_after), "\n")
cat("t-statistic:", t_test_result$statistic, "\n")
cat("p-value:", t_test_result$p.value, "\n")

# Step 6: Decision
if (t_test_result$p.value < 0.05) {
  cat("Conclusion: Reject H₀. After-speed mean is GREATER (α=0.05).\n")
} else {
  cat("Conclusion: Fail to reject H₀. No evidence after > before.\n")
}

################################
# 8
# Use a Mann-Whitney-Wilcoxon test at the α=5% significance level to assess whether the distributions
# of speeds before and after are equal. Draw density plots using before and after speed data. Interpret the
# results based on both the test and drawing.
################################
# Load libraries
library(ggplot2)

# Step 1: Data Prep
speed_before <- speed_data$speed_before
speed_after <- na.omit(speed_data$speed_after)

# Step 2: Mann-Whitney Test
wilcox_result <- wilcox.test(speed_before, speed_after, 
                             alternative = "two.sided",
                             conf.int = TRUE)
cat("--- Mann-Whitney-Wilcoxon Test ---\n")
print(wilcox_result)

# Step 3: Density Plot
plot_data <- data.frame(
  speed = c(speed_before, speed_after),
  group = rep(c("Before", "After"), 
              c(length(speed_before), length(speed_after)))
)

ggplot(plot_data, aes(x = speed, fill = group)) +
  geom_density(alpha = 0.5) +
  labs(title = "Speed Distributions Before vs. After Legislative Changes",
       x = "Speed (mph)",
       y = "Density") +
  theme_minimal()

# Step 4: Effect Size (Optional)
# Hodges-Lehmann estimator (pseudo-median difference)
cat("\nHodges-Lehmann Estimator (Median Difference):", wilcox_result$estimate, "\n")
