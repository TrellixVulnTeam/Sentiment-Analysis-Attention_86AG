import numpy as np
from sklearn import metrics
import torch
import time
import torch.nn as nn
import matplotlib.pyplot as plt
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def train_and_eval(model,train_iter, valid_iter, optimizer, loss_fn =nn.NLLLoss() , epochs=20,dir='project/Models/',name='RNN',data_name = 'SST3', verbose=True):
    checkpoint_filename = dir+ data_name+'_' +name+'.pt'
    train_accur = []
    test_accur = []
    train_losses = []
    test_losses = []
    best_acc = 0 #for best model
    save_checkpoint = False
    #TRAIN!!!!
    for epoch_idx in range(epochs):
        model.train()
        total_loss, num_correct = 0, 0
        total_samples = 0
        start_time = time.time()

        for train_batch in train_iter:
            X, y = train_batch.text.cuda(), train_batch.label.cuda()

            # Forward pass
            y_pred_log_proba = model(X)

            # Backward pass
            optimizer.zero_grad()
            loss = loss_fn(y_pred_log_proba, y)
            loss.backward()

            # Weight updates
            optimizer.step()

            # Calculate accuracy
            total_loss += loss.item()
            y_pred = torch.argmax(y_pred_log_proba, dim=1)
            num_correct += torch.sum(y_pred == y).float().item()
            total_samples+= len(train_batch) 

        train_loss = total_loss /len(train_iter)
        train_acc = num_correct / total_samples
        
        train_accur.append(num_correct /(total_samples))
        
        total_loss, num_correct = 0, 0
        total_samples = 0
        model.eval()
        #evaluate over validation
        with torch.no_grad():
            for val_batch in valid_iter:
                X, y = val_batch.text.cuda(), val_batch.label.cuda()
                y = torch.autograd.Variable(y).long()

                y_pred_log_proba = model(X)
                loss = loss_fn(y_pred_log_proba, y)
                total_loss += loss.item()
                y_pred = torch.argmax(y_pred_log_proba, dim=1)
                num_correct += torch.sum(y_pred == y).float().item()
                total_samples+= len(train_batch)
        
        if verbose:
            print(f"Epoch #{epoch_idx},train loss={train_loss:.3f},train accuracy={train_acc:.3f}, validation accuracy={num_correct /(total_samples):.3f}, elapsed={time.time()-start_time:.1f} sec")
        test_accur.append(num_correct /(total_samples))
        
        if test_accur[-1] >= best_acc:
            save_checkpoint = True
            best_acc = test_accur[-1]
        
        train_losses.append(train_loss)
        test_losses.append(num_correct /(total_samples))
        if save_checkpoint and checkpoint_filename is not None:
            saved_state = dict(best_acc=best_acc,model_state=model.state_dict())
            torch.save(saved_state, checkpoint_filename)
            if verbose:
                print(f"*** Saved checkpoint {checkpoint_filename} " f"at epoch {epoch_idx+1}")
            save_checkpoint = False
               

    saved_state = torch.load(checkpoint_filename, map_location=device)
    model.load_state_dict(saved_state['model_state'])
    
    return train_accur, test_accur,train_losses,test_losses
        
        
        
                
def clip_gradient(model, clip_value):
    params = list(filter(lambda p: p.grad is not None, model.parameters()))
    for p in params:
        p.grad.data.clamp_(-clip_value, clip_value)  

    

        
def present_accuracy(model, dataloader,classes=3,show=True):
    model.eval() # put in evaluation mode
    total_correct = 0
    total = 0
    confusion_matrix = np.zeros([classes,classes], int)
    with torch.no_grad():
        for data in dataloader:
            X, y = data.text.cuda(), data.label.cuda()
            y_pred_log_proba = model(X)
            predicted = torch.argmax(y_pred_log_proba, dim=1)
            total += len(data)
            total_correct += (predicted == y).sum().item()
            for i, l in enumerate(y):
                confusion_matrix[l.item(), predicted[i].item()] += 1 

    model_accuracy = total_correct / total * 100
    print("Test accuracy: {:.3f}%".format(model_accuracy))
    if show:
        if classes ==   2:
            labels = ('0','1')
        elif classes == 3:
            labels = ('0','1','2')
        elif classes == 5:
            labels = ('0','1','2','3','4')
        
        fig, ax = plt.subplots(1,1,figsize=(8,6))
        ax.matshow(confusion_matrix, aspect='auto', vmin=0, vmax=1000, cmap=plt.get_cmap('Blues'))
        plt.ylabel('Actual Category')
        plt.yticks(range(classes), labels)
        plt.xlabel('Predicted Category')
        plt.xticks(range(classes), labels)
        plt.show()
    return model_accuracy

def print_stats(model, dataloader,classes=3):
    model.eval() # put in evaluation mode
    trues = []
    preds = []
    with torch.no_grad():
        for data in dataloader:
            X, y = data.text.cuda(), data.label.cuda()
            trues+=list(y.cpu())
            y_pred_log_proba = model(X)
            predicted = torch.argmax(y_pred_log_proba, dim=1)
            preds+= list(predicted.cpu())            
    print(metrics.classification_report(trues, preds, digits=classes))