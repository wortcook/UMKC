library(ISLR2)
set.seed(6472)

fit_and_evaluate <- function(data_source, poly_size, Y, X, train){
  fit <- lm(Y ~ poly(X, degree=poly_size), data=data_source, subset=train)
  mean((Y - predict(fit, data_source))[-train]^2)
}

attach(Auto)

# SECTION 1
train <- sample(392,196)
print("############ 50/50 ######")
print('LINEAR ##########')
print(gen_fitsAuto(Auto,1,mpg,horsepower, train))
print('POLY-2 ##########')
print(gen_fitsAuto(Auto,2,mpg,horsepower, train))
print('POLY-3 ##########')
print(gen_fitsAuto(Auto,3,mpg,horsepower, train))

# SECTION 2
train <- sample(392,236)
print("############ 60/40 ######")
print('LINEAR ##########')
print(gen_fitsAuto(Auto,1,mpg,horsepower, train))
print('POLY-2 ##########')
print(gen_fitsAuto(Auto,2,mpg,horsepower, train))
print('POLY-3 ##########')
print(gen_fitsAuto(Auto,3,mpg,horsepower, train))

train <- sample(392,275)
print("############ 70/30 ######")
print('LINEAR ##########')
print(gen_fitsAuto(Auto,1,mpg,horsepower, train))
print('POLY-2 ##########')
print(gen_fitsAuto(Auto,2,mpg,horsepower, train))
print('POLY-3 ##########')
print(gen_fitsAuto(Auto,3,mpg,horsepower, train))

train <- sample(392,314)
print("############ 80/20 ######")
print('LINEAR ##########')
print(gen_fitsAuto(Auto,1,mpg,horsepower, train))
print('POLY-2 ##########')
print(gen_fitsAuto(Auto,2,mpg,horsepower, train))
print('POLY-3 ##########')
print(gen_fitsAuto(Auto,3,mpg,horsepower, train))

#SECTION 3
library(boot)
loocv_error <- rep(0, 8)
for (i in 1:8) {
  glm.fit <- glm(mpg ~ poly(displacement, i), data = Auto)
  loocv_error[i] <- cv.glm(Auto, glm.fit)$delta[1]
}
print("##### LOOCV ########")
print(loocv_error)

#SECTION 4
kfold_5 <- rep(0, 5)
for (i in 1:5) {
  glm.fit <- glm(mpg ~ poly(weight, i), data = Auto)
  kfold_5[i] <- cv.glm(Auto, glm.fit, K = 5)$delta[1]
}
print("##### K-Fold - 5")
print(kfold_5)

kfold_10 <- rep(0, 10)
for (i in 1:10) {
  glm.fit <- glm(mpg ~ poly(weight, i), data = Auto)
  kfold_10[i] <- cv.glm(Auto, glm.fit, K = 10)$delta[1]
}
print("##### K-Fold - 10")
print(kfold_10)

#SECTION 5
boot_func <- function(data, index){
  coef(
    lm(mpg ~ horsepower + I(horsepower^2), 
       data = data, subset = index)
  )
}
boot_func(Auto, 1:392)

boot_func(Auto, sample(392,392,replace=T))

boot(Auto, boot_func, 250)
boot(Auto, boot_func, 500)
boot(Auto, boot_func, 2500)
summary(
  lm(mpg ~ horsepower + I(horsepower^2), data = Auto)
)$coef
