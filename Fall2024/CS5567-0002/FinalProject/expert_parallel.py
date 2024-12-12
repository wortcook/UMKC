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

filter_counts =  [32, 16, 16, 32, 32, 64, 64]
kernel_sizes  =  [3,  13, 11,  9,  7,  5,  3]



from keras.callbacks import LearningRateScheduler

dense_size = 32

for j in range(5):
    for i in range(len(filter_counts)):
        #convert X_sample to float32

        #if the model file already exists, skip it
        inner_model = None

        try:
            inner_model = models.load_model(f'model_{filter_counts[i]}_{kernel_sizes[i]}_{FILE_VERSION_SUFFIX}.keras', compile=False)
            print(f'Loaded model_{filter_counts[i]}_{kernel_sizes[i]}_{FILE_VERSION_SUFFIX}.keras')
            inner_model.trainable = True
        except:

            inner_model = models.Sequential()
            inner_model.add(layers.InputLayer(shape=(32,32,3)))

            inner_model.add(layers.Conv2D(filter_counts[i], (kernel_sizes[i], kernel_sizes[i]), activation='relu', padding='same'))
            inner_model.add(layers.Dropout(0.25))
            inner_model.add(layers.BatchNormalization())

            inner_model.add(layers.Conv2D(2*filter_counts[i], (3, 3), activation='relu', padding='same'))
            inner_model.add(layers.Dropout(0.25))
            inner_model.add(layers.BatchNormalization())
            inner_model.add(layers.MaxPooling2D((2, 2)))

            inner_model.add(layers.Conv2D(4*filter_counts[i], (3, 3), activation='relu', padding='same'))
            inner_model.add(layers.Dropout(0.25))
            inner_model.add(layers.BatchNormalization())
            inner_model.add(layers.MaxPooling2D((2, 2)))

        inner_model.add(layers.GlobalAveragePooling2D())
        inner_model.add(layers.Dense(dense_size, activation='relu'))
        inner_model.add(layers.Dense(10, activation='softmax'))

        print(f"Training model_{filter_counts[i]}_{kernel_sizes[i]}_{FILE_VERSION_SUFFIX}.keras")

        inner_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

        inner_model.fit(X_train, Y_train, epochs=25, validation_data=(X_test,Y_test), verbose=1)

        inner_model.pop(rebuild=True)
        inner_model.pop(rebuild=True)
        inner_model.pop(rebuild=True)

        inner_model.save(f'model_{filter_counts[i]}_{kernel_sizes[i]}_{FILE_VERSION_SUFFIX}.keras')

#load the cifar100 dataset
cifar100 = tf.keras.datasets.cifar100

(X_train, Y_train), (X_test,Y_test) = cifar100.load_data()

X_train = X_train.astype('float32') / 255
X_test = X_test.astype('float32') / 255

Y_train = to_categorical(Y_train)
Y_test = to_categorical(Y_test)

print(Y_test.shape)

the_models = []

for i in range(len(filter_counts)):
    inner_model = models.load_model(f'model_{filter_counts[i]}_{kernel_sizes[i]}_{FILE_VERSION_SUFFIX}.keras')
    print(f'Loaded model_{filter_counts[i]}_{kernel_sizes[i]}_{FILE_VERSION_SUFFIX}.keras')
    inner_model.trainable = False

    #Fine tune the model
    model = models.Sequential()
    model.add(layers.InputLayer(shape=(32,32,3)))
    model.add(inner_model)
    model.add(layers.GlobalAveragePooling2D())
    model.add(layers.BatchNormalization())
    model.add(layers.Dense(256, activation='relu'))
    model.add(layers.Dense(100, activation='softmax'))

    optimizer = optimizers.Adam(learning_rate=0.00005)

    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])
    model.fit(X_train, Y_train, epochs=20, batch_size=64)

    model.trainable = False

    the_models.append(model)



#load the cifar100 dataset
cifar100 = tf.keras.datasets.cifar100

(X_train, Y_train), (X_test,Y_test) = cifar100.load_data()

X_train = X_train.astype('float32') / 255
X_test = X_test.astype('float32') / 255

Y_train = to_categorical(Y_train)
Y_test = to_categorical(Y_test)

#make the models trainable
for model in the_models:
    model.trainable = False


#Construct an ensemble model
inp = layers.Input(shape=(32,32,3))
x = layers.Add()([model(inp) for model in the_models])
x = layers.Dense(128, activation='relu')(x)
x = layers.Dense(100, activation='softmax')(x)

ensemble_model = models.Model(inp, x)

print(ensemble_model.summary())
print(Y_train.shape)
print(X_train.shape)

ensemble_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

ensemble_model.fit(X_train, Y_train, epochs=20, batch_size=64)

#Create a confusion matrix
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report

import numpy as np

Y_pred = ensemble_model.predict(X_test)

print(Y_pred.shape)
print(Y_test.shape)

yp_max = np.argmax(Y_pred, axis=1)
yt_max = np.argmax(Y_test, axis=1)

#print the metrics
print(classification_report(yt_max, yp_max))

print(confusion_matrix(yt_max, yp_max))
