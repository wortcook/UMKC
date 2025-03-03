library(e1071)

# Assuming ms.drg.2018 is already loaded
df = ms.drg.2018


########################
# Question 1
########################
# Get subset of data where state is MO and CA
df.mo = df[df$state == 'MO',]
df.ca = df[df$state == 'CA',]

# Calculate summary statistics
summary_stats <- function(data, column, stats_functions) {
  sapply(stats_functions, function(f) f(data[[column]], na.rm = TRUE))
}

columns <- c("total_discharges", "average_covered_charges", "average_total_payments", "average_medicare_payments")

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
  State = rep(c("MO", "CA"), each = length(columns)),
  Metric = rep(columns, 2),
  Mean = numeric(2 * length(columns)),
  Median = numeric(2 * length(columns)),
  SD = numeric(2 * length(columns)),
  Skewness = numeric(2 * length(columns)),
  Kurtosis = numeric(2 * length(columns))
)

# Fill the data frame with summary statistics
for (i in 1:length(columns)) {
  mo_stats <- summary_stats(df.mo, columns[i], stats_functions)
  ca_stats <- summary_stats(df.ca, columns[i], stats_functions)
  
  summary_table[i, 3:7] <- mo_stats
  summary_table[i + length(columns), 3:7] <- ca_stats
}


# Print the summary table
print(summary_table)

########################
# Question 2
########################
#First filter out any rows not within 2 standard deviations of the mean
df.mo.filtered = df.mo[abs(df.mo$average_total_payments - mean(df.mo$average_total_payments)) < 2*sd(df.mo$average_total_payments),]
df.ca.filtered = df.ca[abs(df.ca$average_total_payments - mean(df.ca$average_total_payments)) < 2*sd(df.ca$average_total_payments),]

#Create a combined boxplot of the two states
boxplot( df.mo.filtered$average_total_payments, 
         df.ca.filtered$average_total_payments, 
         names = c("MO", "CA"), 
         xlab = "State", 
         ylab = "Average Total Payments", 
         main = "Average Total Payments by State",
         col = c("darkgreen", "cadetblue2"),
         horizontal = TRUE
      )

########################
# Question 3
########################
df.urban = df[df$state=='CA' | df$state=='NY' | df$state=='FL',]
df.mixed = df[df$state=='NM' | df$state=='ND' | df$state=='WY',]

columns <- c("average_covered_charges")

first_quartile <- function(x, na.rm) {
  quantile(x, 0.25, na.rm = na.rm)
}

second_quartile <- function(x, na.rm) {
  quantile(x, 0.5, na.rm = na.rm)
}

third_quartile <- function(x, na.rm) {
  quantile(x, 0.75, na.rm = na.rm)
}

# List of functions to generate statistics
stats_functions <- list(
  mean = mean,
  median = median,
  sd = sd,
  skewness = skewness,
  kurtosis = kurtosis,
  min = min,
  max = max,
  first_quartile = first_quartile,
  second_quartile = second_quartile,
  third_quartile = third_quartile
)

# Create a data frame to store summary statistics
summary_table <- data.frame(
  Type = rep(c("Urban", "Mixed"), each = length(columns)),
  Metric = rep(columns, 2),
  Mean = numeric(2 * length(columns)),
  Median = numeric(2 * length(columns)),
  SD = numeric(2 * length(columns)),
  Skewness = numeric(2 * length(columns)),
  Kurtosis = numeric(2 * length(columns)),
  Minimum = numeric(2 * length(columns)),
  Maximum = numeric(2 * length(columns)),
  First_Quartile = numeric(2 * length(columns)),
  Second_Quartile = numeric(2 * length(columns)),
  Third_Quartile = numeric(2 * length(columns))
)

# Fill the data frame with summary statistics
for (i in 1:length(columns)) {
  urban_stats <- summary_stats(df.urban, columns[i], stats_functions)
  mixed_stats <- summary_stats(df.mixed, columns[i], stats_functions)
  
  summary_table[i, 3:12] <- urban_stats
  summary_table[i + length(columns), 3:12] <- mixed_stats
}


# Print the summary table
print(summary_table)

########################
# Question 4
########################

library(plyr)

#Create new dataframe only constaining rows with drg_definition containing "CARDIAC"
# and state = CA, WY, ID, NY, KS, and MO
df.cardiac = df[grepl("CARDIAC", df$drg_definition) & df$state %in% c("CA", "WY", "ID", "NY", "KS", "MO"),]

#Using ddply find summary statistics for state = CA, WY, ID, NY, KS, and MO and calculate average total_discharges,
#median total_discharges, average covered_charges, and average total_payments
df.cardiac.summary = ddply(df.cardiac, .(state), summarise, 
                           avg_total_discharges = mean(total_discharges, na.rm = TRUE),
                           median_total_discharges = median(total_discharges, na.rm = TRUE),
                           avg_covered_charges = mean(average_covered_charges, na.rm = TRUE),
                           avg_total_payments = mean(average_total_payments, na.rm = TRUE)
                          )


print(df.cardiac.summary)

########################
# Question 5
########################

#Now create a bar plot of avg_total_discharges for each state give each state a different shade of green
# Set the max value of the y-axis to the max value of avg_total_discharges in the data
max_y = max(df.cardiac.summary$avg_total_discharges)

barplot(df.cardiac.summary$avg_total_discharges, 
        names.arg = df.cardiac.summary$state, 
        xlab = "State", 
        ylab = "Average Total Discharges", 
        main = "Average Total Discharges by State",
        col = c("darkgreen", "green", "lightgreen", "forestgreen", "limegreen", "seagreen"),
        ylim = c(0, max_y + 10)
        )
