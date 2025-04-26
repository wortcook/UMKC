#CS5590-0025 Homework 1                                      Thomas Jones
#Date: March 4, 2025                                             08206472
library(e1071)
library(EnvStats)

#LOAD THE DATA FROM LOCAL DIRECTORY
df <- read.csv("/Users/thomasjones/workspace/UMKC/Spring2025/CS5590-0021/hw2/speed.data.csv")

head(df)

speed_before <- df$speed_before
speed_before.n <- length(speed_before)

speed_after <- df$speed_after
speed_after.cleaned = speed_after[!is.na(speed_after)]
speed_after.n <- length(df$speed_after) - colSums(is.na(df))["speed_after"]

############################
# 1
# Generate boxplots for vehicular before and after speeds data. Discuss and compare the results. 
############################

boxplot( speed_before,
         speed_after,
         names = c("Speed Before", "Speed After"), 
         xlab = "Before/After", 
         ylab = "MPH", 
         main = "Average MPH Before/After Legislation",
         col = c("slategray", "slategray2"),
         horizontal = FALSE
)

# Calculate summary statistics
summary_stats <- function(data, column, stats_functions) {
  sapply(stats_functions, function(f) f(data[[column]], na.rm = TRUE))
}

columns <- c("speed_before", "speed_after")

# List of functions to generate statistics
stats_functions <- list(
  mean = mean,
  median = median,
  sd = sd,
  skewness = skewness,
  kurtosis = kurtosis
)

# Create a data frame to store summary statistics
summary_table <- data.frame(
  Measure = rep(c("Before", "After")),
  Mean = numeric(1),
  Median = numeric(1),
  SD = numeric(1),
  Skewness = numeric(1),
  Kurtosis = numeric(1)
)

# Fill the data frame with summary statistics
for (i in 1:length(columns)) {
  stats <- summary_stats(df, columns[i], stats_functions)
  summary_table[i, 2:6] <- stats
}

# Print the summary table
print(summary_table)


############################
# 2
# Generate 99% confidence intervals for mean vehicular before-speed data, assuming the population
# variance is unknown. Explain each step and interpret the results. 
############################
sprintf("Length of data: %i",speed_before.n)

speed_before.sample_mean <- mean(speed_before, na.rm = TRUE)

sprintf("Sample mean: %.2f", speed_before.sample_mean)

speed_before.sample_sd <- sd(speed_before, na.rm = TRUE)

sprintf("Sample standard deviation: %.2f", speed_before.sample_sd)

speed_before.standard_error <- speed_before.sample_sd / sqrt(speed_before.n)

sprintf("Standard error: %.2f", speed_before.standard_error)

t_critical <- qt(0.995, df = speed_before.n - 1)

sprintf("t-critical: %.2f", t_critical)

ci_lower <- speed_before.sample_mean - t_critical * speed_before.standard_error
ci_upper <- speed_before.sample_mean + t_critical * speed_before.standard_error

print("99% Confidence Interval for Mean Before-Speed:")
sprintf("Lower bound: %.2f", ci_lower)
sprintf("Upper bound: %.2f", ci_upper)

############################
# 3
# Generate 90% confidence intervals for the variance of after-speed data. Explain each step and interpret
# the results.
############################
# Extract after-speed data
sprintf("Length of data: %i",speed_after.n)

speed_after.sample_var <- var(speed_after, na.rm=TRUE)

sprintf("Sample variance: %.2f", speed_after.sample_var)

# Chi-squared critical values (for 90% CI)
alpha <- 0.10
chi_sq_lower <- qchisq(1 - alpha/2, df = n - 1)
chi_sq_upper <- qchisq(alpha/2, df = n - 1)

sprintf("Chi-squared lower: %.2f", chi_sq_lower)
sprintf("Chi-squared upper: %.2f", chi_sq_upper)

# Calculate CI for variance
ci_lower_var <- ((n - 1) * sample_var) / chi_sq_lower
ci_upper_var <- ((n - 1) * sample_var) / chi_sq_upper

# Print results
print("90% Confidence Interval for After-Speed Variance:\n")
sprintf("Lower bound: %.2f", ci_lower_var)
sprintf("Upper bound: %.2f\n", ci_upper_var)

###############################
# 4
# Test whether the mean speed is equal to 65 mph after repealing the speed limit at the α=1%
# significance level. Write each step of the hypotheses test and interpret the results. 
###############################
speed_after.sample_mean <- mean(speed_after,na.rm = TRUE)

sprintf("Speed after sample mean: %.2f", speed_after.sample_mean)

speed_after.sample_sd <- sd(speed_after,na.rm = TRUE)

test_speed <- 65
t_stat <- (speed_after.sample_mean - test_speed) / ((speed_after.sample_sd/sqrt(speed_after.n-1)))
sprintf("t-test statistic: %.2f", t_stat)

p_value = 2*pt(abs(t_stat), df=(speed_after.n - 1))

sprintf("p-value: %.4f", p_value)


if (p_value > significance_level) {
  sprintf("Null hypothesis rejected, the actual mean speed is not %.0f", test_speed)
} else {
  sprintf("Failed to reject null hypothesis, the actual mean speed is %.0f", test_speed)
}

the_test = t.test(x=speed_after, mu=test_speed, conf.level=0.995)

print(the_test)


##############################
# 5
# Test whether the variance of after-speed data is less than 18 mph at the α=5% significance level. Write
# each step of the hypotheses test and interpret the results. 
#############################
test_value <- 40

sprintf("Sample variance: %.2f", speed_after.sample_var)

chi_sq_stat <- (n - 1) * speed_after.sample_var / test_value

sprintf("Chi-squared: %.2f", chi_sq_stat)

alpha <- 0.05
chi_sq_critical <- qchisq(alpha, df = n - 1)

sprintf("Critical value: %.2f", chi_sq_critical)

if (chi_sq_stat < chi_sq_critical) {
  sprintf("Failed to reject null hypothesis, greater less than 18  %.0f", test_value)
} else {
  sprintf("Null hypothesis rejected, variance less than 18  than %.0f", test_value)
}

the_test = varTest(x=speed_after.cleaned, alternative="less", sigma.squared=test_value)

print(the_test)

#############################
# 6
# Test that the vehicular before-speed variance is less than after-speed at the α=10% significance level.
# Write each step of the hypotheses test and interpret the results.
#############################
speed_before.sample_var = var(speed_before, na.rm = TRUE)

sprintf("Speed before variance: %.2f", speed_before.sample_var)
sprintf("Speed after variance: %.2f", speed_after.sample_var)

f_stat <- speed_before.sample_var / speed_after.sample_var

sprintf("f_stat: %.2f", f_stat)

alpha <- 0.10

f_critical <- qf(alpha, df1 = speed_before.n - 1, df2 = speed_after.n -1)

sprintf("f_critical: %.2f", f_critical)

# Decision
if (f_stat < f_critical) {
  cat("Before-speed variance is less than after.\n")
} else {
  cat("No evidence before variance < after.\n")
}

the_test = var.test(speed_before, speed_after, alternative="less", conf.level = 0.90)
print(the_test)

#################################
# 7
# Test that the vehicular after-speed mean is greater than before-speed at the α=5% significance level.
# Write each step of the hypotheses test and interpret the results. 
#################################
sbv = speed_before.sample_var/speed_before.n
sav = speed_after.sample_var/speed_after.n

degrees_freedom = ((sbv + sav)^2)/( ((sbv^2)/(speed_before.n - 1)) + ((sav)^2)/(speed_after.n - 1))
                  
sprintf("Degrees of freedom: %.2f", degrees_freedom)

t_stat = ((speed_before.sample_mean - speed_after.sample_mean))/sqrt(sbv+sav)

sprintf("t-statistic: %.2f", t_stat)

p_value = dt(t_stat, degrees_freedom)

sprintf("p-value: %.2f", p_value)

alpha = 0.05

if(p_value < alpha){
  print("Null hypothesis rejected, speed after is greater than speed before.")
}else{
  print("Null hypotheis not rejected, no evidence")
}

var_test <- var.test(speed_before, speed_after.cleaned)
equal_var <- var_test$p.value > 0.05

# Step 4: Run t-test
t_test_result <- t.test(speed_after.cleaned, speed_before,
                        alternative = "greater",
                        var.equal = equal_var)

print(t_test_result)

################################
# 8
# Use a Mann-Whitney-Wilcoxon test at the α=5% significance level to assess whether the distributions
# of speeds before and after are equal. Draw density plots using before and after speed data. Interpret the
# results based on both the test and drawing.
################################
wilcox_result <- wilcox.test(speed_before, speed_after.cleaned, 
                             alternative = "two.sided",
                             conf.int = TRUE)

print(wilcox_result)

alpha = 0.05

if(wilcox_result$p.value < alpha){
  print("The two distributions ")
}

plot_data <- data.frame(
  speed = c(speed_before, speed_after),
  group = rep(c("Before", "After"), 
              c(length(speed_before), length(speed_after)))
)


d_before <- density(speed_before, na.rm = TRUE)
d_after <- density(speed_after, na.rm = TRUE)

xlim <- range(c(d_before$x, d_after$x))
ylim <- range(c(d_before$y, d_after$y))

plot(d_before, 
     xlim = xlim, ylim = ylim,
     col = "slategray", lwd = 2,
     main = "Speed Distributions Before vs. After Legislative Changes",
     xlab = "Speed (mph)", ylab = "Density")
lines(d_after, col = "slategray2", lwd = 2)
legend("topright", 
       legend = c("Before", "After"),
       col = c("slategray", "slategray2"), lwd = 2)

