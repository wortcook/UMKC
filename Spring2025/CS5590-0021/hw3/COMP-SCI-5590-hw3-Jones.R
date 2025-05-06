#LOAD THE DATA FROM LOCAL DIRECTORY
df <- read.csv("/Users/thomasjones/workspace/UMKC/Spring2025/CS5590-0021/hw3/car.data.csv")

head(df)

library(dplyr)

#Get an idea about some basic feature stats
feature_stats <- function(df, fname) {
  print(fname)
  print(sprintf("mean     : %.1f",mean(df[[fname]],na.rm = TRUE)))
  print(sprintf("median.  : %.1f",median(df[[fname]],na.rm = TRUE)))
  print(sprintf("variance : %.1f",var(df[[fname]],na.rm = TRUE)))
  print(sprintf("min      : %.1f",min(df[[fname]],na.rm = TRUE)))
  print(sprintf("max      : %.1f",max(df[[fname]],na.rm = TRUE)))
}

feature_stats(df,"mpg")
feature_stats(df,"cylinders")
feature_stats(df, "displacement")
feature_stats(df, "hp")
feature_stats(df, "weight")
feature_stats(df, "acceleration")
feature_stats(df, "modelyr")
feature_stats(df, "origin")
feature_stats(df, "foreign")


## Breakdown of foreign, i.e. how many North American origin cars are foreign?
df_na_foreign <- df %>% filter((origin==1) & (foreign==1))
head(df_na_foreign)

