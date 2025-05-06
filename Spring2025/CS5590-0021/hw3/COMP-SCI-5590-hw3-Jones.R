#LOAD THE DATA FROM LOCAL DIRECTORY
#df <- read.csv("/Users/thomasjones/workspace/UMKC/Spring2025/CS5590-0021/hw3/car.data.csv")
df <- read.csv("/Users/wortcook/Workspace/UMKC/Spring2025/CS5590-0021/hw3/car.data.csv")

head(df)

#1/2
summary(df[, c("mpg", "cylinders", "displacement", "hp", "weight", "acceleration","modelyr","origin","foreign")])

plot(df$cylinders, df$mpg, xlab = "Cylinders", ylab="MPG")
plot(df$displacement, df$mpg, xlab="Displacement", ylab="MPG")
plot(df$hp, df$mpg, xlab="HP", ylab="MPG")
plot(df$weight, df$mpg, xlab="Weight", ylab="MPG")
plot(df$acceleration, df$mpg, xlab="Acceleration", ylab="MPG")
plot(df$modelyr, df$mpg, xlab="Model Year", ylab="MPG")
plot(df$origin, df$mpg, xlab="Origin", ylab="MPG")


df_mod <- df[,!names(df) %in% c("name","foreign")]
df_mod <- df_mod[, !grepl("^modyr\\d+",names(df_mod))]

#3 - Correlation
df_mod.cor <- cor(df_mod)

df_mod.cor

#4 - Build Model
library(car)

model1 = lm(formula = mpg ~ cylinders + displacement + hp + weight + acceleration + modelyr + origin, data = df_mod)
summary(model1)

vif(model1)

model2 = lm(formula = mpg ~  weight + acceleration + modelyr + origin, data = df_mod)
summary(model2)

vif(model2)

avPlots(model2)



