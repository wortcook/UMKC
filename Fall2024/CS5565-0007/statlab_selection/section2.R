library(ISLR2)
library(leaps)

Hitters <- na.omit(Hitters)

##ORIGINALS
print("FORWARD WITH 19 **********************")
regfit.fwd <- regsubsets(Salary ~ ., data = Hitters,
                         nvmax = 19, method = "forward")
summary(regfit.fwd)

print("BACKWARD WITH 19 **********************")
regfit.bwd <- regsubsets(Salary ~ ., data = Hitters,
                         nvmax = 19, method = "backward")
summary(regfit.bwd)

##NEW NVMAX
print("FORWARD WITH 12 **********************")
regfit.fwd <- regsubsets(Salary ~ ., data = Hitters,
                         nvmax = 12, method = "forward")
summary(regfit.fwd)

print("BACKWARD WITH 12 **********************")
regfit.bwd <- regsubsets(Salary ~ ., data = Hitters,
                         nvmax = 12, method = "backward")
summary(regfit.bwd)

##########################
#Ridge Regression
##########################
x <- model.matrix(Salary ~ ., Hitters)[, -1]
y <- Hitters$Salary

library(glmnet)
grid <- 10^seq(10, -2, length = 100)
ridge.mod <- glmnet(x, y, alpha = 0, lambda = grid)

predict(ridge.mod, s = 50, type = "coefficients")[1:20, ]

predict(ridge.mod, s = 472, type = "coefficients")[1:20, ]

set.seed(1)
train <- sample(1:nrow(x), nrow(x) / 2)
test <- (-train)
y.test <- y[test]

ridge.mod <- glmnet(x[train, ], y[train], alpha = 0,
                    lambda = grid, thresh = 1e-12)
ridge.pred <- predict(ridge.mod, s = 50, newx = x[test, ])
mean((ridge.pred - y.test)^2)

ridge.mod <- glmnet(x[train, ], y[train], alpha = 0,
                    lambda = grid, thresh = 1e-12)
ridge.pred <- predict(ridge.mod, s = 472, newx = x[test, ])
mean((ridge.pred - y.test)^2)

ridge.mod <- glmnet(x[train, ], y[train], alpha = 0,
                    lambda = grid, thresh = 1e-12)
ridge.pred <- predict(ridge.mod, s = 472000, newx = x[test, ])
mean((ridge.pred - y.test)^2)

#########################
#PARTIAL LEAST SQUARES
#########################
set.seed(1)
train <- sample(1:nrow(x), nrow(x) / 2)
test <- (-train)
y.test <- y[test]

cv.out <- cv.glmnet(x[train, ], y[train], alpha = 0)
plot(cv.out)

set.seed(472)
train <- sample(1:nrow(x), nrow(x) / 2)
test <- (-train)
y.test <- y[test]

cv.out <- cv.glmnet(x[train, ], y[train], alpha = 0)
plot(cv.out)


