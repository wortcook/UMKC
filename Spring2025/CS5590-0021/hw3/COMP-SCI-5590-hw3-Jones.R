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
df_mod <- df_mod[, !grepl("^modelyr",names(df_mod))]

df_mod_num <- df_mod[, !grepl("^modyr\\d+", names(df_mod))]
df_mod_num <- df_mod_num[, !grepl("^origin", names(df_mod_num))]

#3 - Correlation
cor(df_mod_num)


#4 - Build Model
library(car)

#Add dummies for origin
df_mod$origin_na <- ifelse(df_mod$origin == 1,1,0)
df_mod$origin_eu <- ifelse(df_mod$origin == 2,1,0)

model1 = lm(formula = 
              mpg ~ cylinders + displacement + hp + 
              weight + acceleration + origin_na + origin_eu +
              modyr71 + modyr72 + modyr73+ modyr74 + modyr75 +
              + modyr76 + modyr77 + modyr78 + modyr79 + modyr80 +
              + modyr81 + modyr82
            , data = df_mod)
summary(model1)

vif(model1)

model2 = lm(formula = 
              mpg ~ displacement + hp + acceleration + origin_na + origin_eu +
              modyr71 + modyr72 + modyr73+ modyr74 + modyr75 +
              modyr76 + modyr77 + modyr78 + modyr79 + modyr80 +
              modyr81 + modyr82
            , data = df_mod)

summary(model2)

vif(model2)

#5
install.packages('car')
install.packages('alr4')
install.packages('faraway')

#Identifying unusual and influential data
# Scatterplot
library(car)
library(alr4)
library(faraway)

model2_H0 <- c("displacement", "hp", "acceleration", "origin_na", "origin_eu", 
               "modyr71", "modyr72", "modyr73", "modyr74", "modyr75", "modyr76",
               "modyr77", "modyr78", "modyr79", "modyr80", "modyr81", "modyr82")
linearHypothesis(model2, model2_H0)

#residualPlots(model2)

df_mod$displacement2 <- log(df_mod$displacement)

df_mod$hp2 <- log(df_mod$hp)

df_mod$acceleration2 <- log(df_mod$acceleration)


model3 = lm(formula = 
              mpg ~ displacement2 + hp2 + acceleration2 + origin_na + origin_eu +
              modyr71 + modyr72 + modyr73+ modyr74 + modyr75 +
              modyr76 + modyr77 + modyr78 + modyr79 + modyr80 +
              modyr81 + modyr82
            , data = df_mod)

summary(model3)

vif(model3)

model3_H0 <- c("displacement2", "hp2", "acceleration2", "origin_na", "origin_eu", 
               "modyr71", "modyr72", "modyr73", "modyr74", "modyr75", "modyr76",
               "modyr77", "modyr78", "modyr79", "modyr80", "modyr81", "modyr82")
linearHypothesis(model3, model3_H0)


#residualPlots(model3)

df_mod$mpg2 = log(df_mod$mpg)

model4 = lm(formula = 
              mpg2 ~ displacement2 + hp2 + acceleration2 + origin_na + origin_eu +
              modyr71 + modyr72 + modyr73+ modyr74 + modyr75 +
              modyr76 + modyr77 + modyr78 + modyr79 + modyr80 +
              modyr81 + modyr82 ,data = df_mod)

summary(model4)

vif(model4)

model4_H0 <- c("displacement2", "hp2", "acceleration2", "origin_na", "origin_eu", 
               "modyr71", "modyr72", "modyr73", "modyr74", "modyr75", "modyr76",
               "modyr77", "modyr78", "modyr79", "modyr80", "modyr81", "modyr82")
linearHypothesis(model4, model4_H0)

#residualPlots(model4)

plot(model4$residuals ~ model4$fitted.values)
abline(h = 0, lty = 2)

summary(model4)


#Normality of errors
library(MASS)

sresid <- studres(model2)
hist(sresid, freq=FALSE,main="Distribution of Studentized Residuals - Model No Transform",xlab="Residuals of the model")
xfit <- seq(min(sresid),max(sresid),length=40)
yfit <- dnorm(xfit)
lines(xfit, yfit)

sresid <- studres(model3)
hist(sresid, freq=FALSE,main="Distribution of Studentized Residuals - Model Log Features",xlab="Residuals of the model")
xfit <- seq(min(sresid),max(sresid),length=40)
yfit <- dnorm(xfit)
lines(xfit, yfit)

sresid <- studres(model4)
hist(sresid, freq=FALSE,main="Distribution of Studentized Residuals - Model Log Features/MPG",xlab="Residuals of the model")
xfit <- seq(min(sresid),max(sresid),length=40)
yfit <- dnorm(xfit)
lines(xfit, yfit)

# Normality of residuals
qqnorm(model4$residuals)  #Normal Quantile to Quantile plot
qqline(model4$residuals) 

#Outliers
scatterplotMatrix( ~mpg + displacement + hp + acceleration + origin + modelyr, data = df)

#Identifying leverages
#a vector containing the diagonal of the 'hat' matrix
h <- influence(model4)$hat
#half normal plot of leverage from package faraway
halfnorm(influence(model4)$hat, ylab = "leverage")

#Identifying influential observations
#Cook's distance is a measure for influence points. A point with high level of cook's distance is considers as a point with high influence point.
cutoff <- 4/((nrow(df_mod)-length(model4$coefficients)-2))
plot(model4, which = 4, cook.levels = cutoff)
abline(h = cutoff)


#Identifying outliers
# Standardized residuals
res.std <- rstandard(model4) #Standardized residuals stored in vector res.std 

#plot Standardized residual in y axis. X axis will be the index or row names
plot(res.std, ylab="Standardized Residual", ylim=c(-3.5,3.5))

#add horizontal lines 3 and -3 to identify extreme values
abline(h =c(-3,0,3), lty = 2)

#find out which data point is outside of 3 standard deviation cut-off
#index is row numbers of those point
index <- which(res.std > 3 | res.std < -3)

#Add the mpg value for those that are outside the range
text(index-20, res.std[index] , labels = df_mod$mpg[index])

#Issues of independence
#residual plot vs. mpg
plot(model4$residuals ~ df_mod$mpg2)

plot(df_mod$mpg ~ df_mod$displacement)
plot(df_mod$mpg2 ~ df_mod$displacement2)

#sanity check
test_mpg <- 7.604 - 0.2432 * log(191.5) - 0.5107 * log(103.5) - 0.3514 * log(15.6) - 0.0364 + 0.0181
test_mpg
exp(test_mpg)

#6 Hypothesis test
df.american = df[df$foreign==0,]
df.foreign  = df[df$foreign==1,]

df.american.n = length(df.american)
df.foreign.n  = length(df.foreign)

#This is our target
df.american.mean_weight = mean(df.american$weight, na.rm = TRUE)
df.american.mean_weight


df.foreign.mean_weight  = mean(df.foreign$weight, na.rm = TRUE)
df.foreign.mean_weight

df.foreign.var_weight  = var(df.foreign$weight, na.rm = TRUE)
df.foreign.var_weight

chi_sq_stat <- (df.foreign.n - 1) * df.foreign.var_weight / df.american.mean_weight
chi_sq_stat

alpha <- 0.05
chi_sq_critical <- qchisq(alpha, df = df.foreign.n - 1)
chi_sq_critical

sprintf("Critical value: %.2f", chi_sq_critical)

if (chi_sq_stat < chi_sq_critical) {
  sprintf("Failed to reject null hypothesis, American cars are heavier")
} else {
  sprintf("Null hypothesis rejected, no evidence that American cars are heavier")
}


