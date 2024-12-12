import tensorflow as tf

import keras

from keras import layers
from keras import models
from keras import optimizers

from keras.utils import to_categorical

import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from tensorflow.keras.preprocessing.image import ImageDataGenerator

import sklearn as sk

import matplotlib.pyplot as plt

def plot_acc_loss(result):
    # function to plot the accuracy and loss graphs
    acc = result.history['accuracy']
    val_acc = result.history['val_accuracy']
    loss = result.history['loss']
    val_loss = result.history['val_loss']

    plt.figure(figsize=(20, 10))
    plt.subplot(1, 2, 1)
    plt.title("Training and Validation Accuracy")
    plt.plot(acc,color = 'green',label = 'Training Acuracy')
    plt.plot(val_acc,color = 'red',label = 'Validation Accuracy')
    plt.legend(loc='lower right')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.subplot(1, 2, 2)
    plt.title('Training and Validation Loss')
    plt.plot(loss,color = 'blue',label = 'Training Loss')
    plt.plot(val_loss,color = 'purple',label = 'Validation Loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(loc='upper right')
    plt.show()


cifar10 = tf.keras.datasets.cifar10
(X_train, Y_train), (X_test,Y_test) = cifar10.load_data()


X_train = X_train.astype('float32') / 255
X_test  = X_test.astype('float32') / 255

Y_train = to_categorical(Y_train, num_classes=10)
Y_test = to_categorical(Y_test, num_classes=10)

cnn_activation = 'elu'
dense_activation = 'elu'

ix_train,ix_val,iy_train,iy_val = train_test_split(X_train, Y_train, test_size = 0.2)


print(ix_train.shape, ix_val.shape, X_test.shape)
print(iy_train.shape, iy_val.shape, Y_test.shape)

train_datagen = ImageDataGenerator(
        rotation_range = 10,
        zoom_range = 0.1,
        width_shift_range = 0.1,
        height_shift_range = 0.1,
        shear_range = 0.1,
        horizontal_flip = True,
        vertical_flip = False
        )
train_datagen.fit(ix_train)


inp = layers.Input(shape=(32,32,3))
#Input layers
x = layers.Conv2D(64, (3,3), activation=cnn_activation, padding='same')(inp)
x = layers.Dropout(0.1)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(64, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.1)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.1)(x)

x = layers.MaxPool2D((2,2))(x)

#Second set of layers

x = layers.Conv2D(128, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.2)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(128, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.2)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.2)(x)

x = layers.MaxPool2D((2,2))(x)

#Third set of layers
x = layers.Conv2D(256, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.3)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(256, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.3)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.3)(x)

x = layers.MaxPool2D((2,2))(x)

#Third set of layers
x = layers.Conv2D(512, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.5)(x)
x1 = layers.BatchNormalization()(x)

x = layers.Conv2D(512, (3,3), activation=cnn_activation, padding='same')(x)
x = layers.Dropout(0.5)(x)
x2 = layers.BatchNormalization()(x)

x = layers.Add()([x1,x2])
x = layers.Dropout(0.5)(x)

inner_model = models.Model(inp, x)

print(inner_model.summary())

headed_model = models.Sequential()
headed_model.add(inner_model)
headed_model.add(layers.Flatten())
headed_model.add(layers.Dense(64, activation=dense_activation))
headed_model.add(layers.Dropout(0.5))
headed_model.add(layers.Dense(64, activation=dense_activation))
headed_model.add(layers.BatchNormalization())
headed_model.add(layers.Dense(10, activation='softmax'))

optimizer_adam = optimizers.Adam()

headed_model.compile(optimizer=optimizer_adam, loss='categorical_crossentropy', metrics=['accuracy'])

result = headed_model.fit(ix_train, iy_train, epochs=50, validation_data=(ix_val,iy_val))

plot_acc_loss(result)

inner_model.save('baseline_custom_head_v5.keras')

Y_pred = headed_model.predict(X_test)

print(Y_pred.shape)
print(Y_test.shape)

yp_max = np.argmax(Y_pred, axis=1)
yt_max = np.argmax(Y_test, axis=1)

#print the metrics
print(classification_report(yt_max, yp_max))

