import tensorflow as tf

import keras

from keras import layers
from keras import models
from keras import optimizers

from keras.utils import to_categorical

from sklearn.model_selection import train_test_split

import sklearn as sk

FILE_VERSION_SUFFIX = "v4"


cifar10 = tf.keras.datasets.cifar10
(X_train, Y_train), (X_test,Y_test) = cifar10.load_data()


X_train = X_train.astype('float32') / 255
X_test = X_test.astype('float32') / 255

Y_train = to_categorical(Y_train)
Y_test = to_categorical(Y_test)

cmi = keras.Input(shape=(None,None,3))

end_models = []

all_activation = 'selu'


inp = layers.Input(shape=(32,32,3))
x1 = layers.Conv2D(32, (3,3), activation=all_activation, padding='same')(inp)
x1 = layers.Dropout(0.25)(x1)
x2 = layers.Conv2D(32, (3,3), activation=all_activation, padding='same')(inp)
x2 = layers.Dropout(0.25)(x2)

# l1c = layers.Concatenate()([x1,x2])
# l1c = layers.Flatten()(l1c)

xl = layers.Add()([x1,x2])
xl = layers.BatchNormalization()(xl)
xr = layers.Subtract()([x1,x2])
xr = layers.BatchNormalization()(xr)

x1 = layers.Conv2D(64, (3,3), activation=all_activation, padding='same')(xl)
x1 = layers.Dropout(0.25)(x1)
x1 = layers.MaxPool2D((2,2))(x1)
x2 = layers.Conv2D(64, (3,3), activation=all_activation, padding='same')(xr)
x2 = layers.Dropout(0.25)(x2)
x2 = layers.MaxPool2D((2,2))(x2)

l2c = layers.Concatenate()([x1,x2])
l2c = layers.Flatten()(l2c)

xl = layers.Add()([x1,x2])
xr = layers.Subtract()([x1,x2])

x1 = layers.Conv2D(128, (3,3), activation=all_activation, padding='same')(xl)
x1 = layers.Dropout(0.25)(x1)
x1 = layers.MaxPool2D((2,2))(x1)
x2 = layers.Conv2D(128, (3,3), activation=all_activation, padding='same')(xr)
x2 = layers.Dropout(0.25)(x2)
x2 = layers.MaxPool2D((2,2))(x2)

# l3c = layers.Concatenate()([x1,x2])
# l3c = layers.Flatten()(l3c)

xl = layers.Add()([x1,x2])
xr = layers.Subtract()([x1,x2])

ga1 = layers.GlobalAveragePooling2D()(xl)
ga2 = layers.GlobalAveragePooling2D()(xr)

dl = layers.Dense(32, activation=all_activation)(ga1)
dl = layers.BatchNormalization()(dl)
dr = layers.Dense(32, activation=all_activation)(ga2)
dr = layers.BatchNormalization()(dr)

c = layers.Concatenate()([dl,dr])
lc = layers.Flatten()(c)

# c = layers.Concatenate()([l1c,l2c,l3c,lc])
c = layers.Concatenate()([lc,l2c])

d = layers.Dense(64, activation=all_activation)(c)
d = layers.Dropout(0.1)(d)

d = layers.Dense(10, activation='softmax')(c)

model = models.Model(inp, d)

print(model.summary())

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

model.fit(X_train, Y_train, epochs=20, batch_size=64, validation_data=(X_test,Y_test))


# #load the cifar100 dataset
# cifar100 = tf.keras.datasets.cifar100

# (X_train, Y_train), (X_test,Y_test) = cifar100.load_data()

# X_train = X_train.astype('float32') / 255
# X_test = X_test.astype('float32') / 255

# Y_train = to_categorical(Y_train)
# Y_test = to_categorical(Y_test)


# #load the cifar100 dataset
# cifar100 = tf.keras.datasets.cifar100

# (X_train, Y_train), (X_test,Y_test) = cifar100.load_data()

# X_train = X_train.astype('float32') / 255
# X_test = X_test.astype('float32') / 255

# Y_train = to_categorical(Y_train)
# Y_test = to_categorical(Y_test)

