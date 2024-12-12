import tensorflow as tf

import keras

from keras import layers
from keras import models
from keras import optimizers

from keras.utils import to_categorical

from sklearn.model_selection import train_test_split

import sklearn as sk

import random

cifar10 = tf.keras.datasets.cifar10
(X_train, Y_train), (X_test,Y_test) = cifar10.load_data()


X_train = X_train.astype('float32') / 255
X_test  = X_test.astype('float32') / 255

Y_train = to_categorical(Y_train)
Y_test = to_categorical(Y_test)

cnn_activation = 'selu'
dense_activation = 'selu'


inp = layers.Input(shape=(32,32,3))
#Input layers
x = layers.Conv2D(64, (3,3), activation=cnn_activation, padding='same')(inp)
x = layers.Dropout(0.1)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(64, (3,3), activation=cnn_activation, padding='same')(x1)
x = layers.Dropout(0.1)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.1)(x)

x = layers.Conv2D(64, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.1)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(64, (3,3), activation=cnn_activation, padding='same')(x1)
x = layers.Dropout(0.1)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.1)(x)

x = layers.MaxPool2D((2,2))(x)

#Second set of layers

x = layers.Conv2D(128, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.2)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(128, (3,3), activation=cnn_activation, padding='same')(x1)
x = layers.Dropout(0.2)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.2)(x)

x = layers.Conv2D(128, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.2)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(128, (3,3), activation=cnn_activation, padding='same')(x1)
x = layers.Dropout(0.2)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.2)(x)

x = layers.MaxPool2D((2,2))(x)

#Third set of layers
x = layers.Conv2D(256, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.3)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(256, (3,3), activation=cnn_activation, padding='same')(x1)
x = layers.Dropout(0.3)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.30)(x)

# Final collection layer

x = layers.Conv2D(512, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.5)(x)
x = layers.BatchNormalization()(x)

inner_model = models.Model(inp, x)



print(inner_model.summary())

headed_model = models.Sequential()
headed_model.add(inner_model)
headed_model.add(layers.Flatten())
headed_model.add(layers.Dense(64, activation=dense_activation))
headed_model.add(layers.Dense(64, activation=dense_activation))
headed_model.add(layers.BatchNormalization())
headed_model.add(layers.Dense(10, activation='softmax'))

optimizer_sgd = optimizers.SGD()
optimizer_adam = optimizers.Adam()

optimizer = optimizer_sgd

headed_model.compile(optimizer=optimizer_adam, loss='categorical_crossentropy', metrics=['accuracy'])


for i in range(50):
    for layer in inner_model.layers:
        #if layer is a convolutional layer
        if isinstance(layer, layers.Conv2D):
            if random.random() < 0.25:
                print(f'Freezing layer {layer.name}')
                layer.trainable = False
            else :
                layer.trainable = True
            

    headed_model.fit(X_train, Y_train, epochs=1, validation_data=(X_test,Y_test))

    if optimizer == optimizer_sgd:
        optimizer = optimizer_adam
    else:
        optimizer = optimizer_sgd

    

# headed_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
# headed_model.fit(X_train, Y_train, epochs=20, batch_size=64, validation_data=(X_test,Y_test))

inner_model.trainable = False


# #load the cifar100 dataset
cifar100 = tf.keras.datasets.cifar100

(X_train, Y_train), (X_test,Y_test) = cifar100.load_data()

X_train = X_train.astype('float32') / 255
X_test  = X_test.astype('float32') / 255

Y_train = to_categorical(Y_train)
Y_test = to_categorical(Y_test)

new_model = models.Sequential()
new_model.add(inner_model)
new_model.add(layers.Flatten())
new_model.add(layers.Dense(64, activation=dense_activation))
new_model.add(layers.Dense(64, activation=dense_activation))
new_model.add(layers.BatchNormalization())
new_model.add(layers.Dense(100, activation='softmax'))

new_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

new_model.fit(X_train, Y_train, epochs=20, batch_size=64, validation_data=(X_test,Y_test))

inner_model.trainable = True
new_model.fit(X_train, Y_train, epochs=2, batch_size=64, validation_data=(X_test,Y_test))

