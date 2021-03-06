import sys, getopt
import imp
import params as p
import VGGish_model as m
import torch
import pickle
import os

from utils import Dataset as d
from utils import trainer as t
from utils import preprocessing as pre

imp.reload(p)
imp.reload(d)
imp.reload(m)
imp.reload(t)
imp.reload(pre)


def prepare(params):
    '''
    reads in a terminal command in the format:

    $ python train.py -d <data dir> -n <# training epochs> -b <batch size>

    options in this command override those in params.py.
    Takes care of handling the terminal input and preprocessing the data
    '''

    #reading in options from terminal command
    print('working out options')
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd:n:b:f:e:', \
                            ['data=', 'nepochs=', 'batchsize=', 'format=', 'epochs='])
    except getopt.GetoptError as err:
        print(err)
        sys.exit()

    for o, a in opts:
        if o in ('-d', '--data'):
            params.data_root = a
        if o in ('-e', '--epochs'):
            params.n_epochs = int(a)
        if o in ('-b', '--batchsize'):
            params.batch_size = int(a)
        if o in ('-f', '--format'):
            params.data_format = a
        if o in ('-n', '--name'):
            params.name = a


    # preprocessing
    if os.path.exists(params.mel_spec_root):
        print('skipping preprocessing and using spectograms in ', params.mel_spec_root)
    else:
        print('preprocessing: generating spectrograms from ', params.data_root)
        if params.data_format == 'mp3':
            pre.process_mp3s_for_training(params)
        if params.data_format == 'wav':
            pre.process_wavs_for_training(params)

    return params


def start_training_with(params):
    '''
    takes a params object and expects ready to be used spectrograms
    in params.mel_spec_root.
    Sets up all requirements for training, runs the training and returns the
    trained model
    '''
    # setup
    device = torch.device(params.device)
    n_classes = len(os.listdir(params.mel_spec_root))
    params.n_classes = n_classes
    print('setting up training for {} classes'.format(n_classes))
    dataset = d.MelSpecDataset(params)
    net = m.VGGish(params)
    net.init_weights()
    net.freeze_bottom()
    new_top = torch.nn.Linear(net.out_dims*512, net.n_classes)
    net.classifier = new_top
    net.to(device)
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(net.parameters())
    trainer = t.Trainer(net, dataset, criterion, optimizer, params, device)

    # starting training
    print('start training on {} for {} epochs'.format(device, params.n_epochs))
    trainer.run_training()

    # saving model weights and class labels
    if params.save_model:
        print('saving weights and class labels')
        net.save_weights()
        print(dataset.labels)
        with open(os.path.join(params.model_zoo, params.name+'.pkl'), 'wb') as f:
            pickle.dump(dataset.labels, f)

    return net, dataset.labels


if __name__ == '__main__':

    params = p.Params()
    params = prepare(params)
    _, _ = start_training_with(params)
    print('done')
