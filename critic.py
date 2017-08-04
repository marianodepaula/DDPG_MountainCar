

import tensorflow as tf
import numpy as np

import tensorflow.contrib.slim as slim

HIDDEN_1 = 400
HIDDEN_2 = 300


class CriticNetwork(object):
    """
    Input to the network is the state and action, output is Q(s,a).
    The action must be obtained from the output of the Actor network.
    """

    def __init__(self, sess, state_dim, action_dim, learning_rate, tau, cell, cell_target, num_actor_vars):
        self.sess = sess
        self.s_dim = state_dim
        self.a_dim = action_dim
        self.learning_rate = learning_rate
        self.tau = tau


        
        self.batch_size = 2 # num of traces
        self.h_size = 300 # the size of the las hidden netowkr before 
        
        # Create the critic network
        self.inputs, self.action, self.out, self.trainLength = self.create_critic_network(cell, 'rnn')

        self.network_params = tf.trainable_variables()[num_actor_vars:]

        # Target Network
        self.target_inputs, self.target_action, self.target_out, self.target_trainLength = self.create_critic_network(cell_target, 'rnn_target')

        self.target_network_params = tf.trainable_variables()[(len(self.network_params) + num_actor_vars):]

        # Op for periodically updating target network with online network
        # weights with regularization
        self.update_target_network_params = \
            [self.target_network_params[i].assign(tf.multiply(self.network_params[i], self.tau) + tf.multiply(self.target_network_params[i], 1. - self.tau))
                for i in range(len(self.target_network_params))]

        # Network target (y_i)
        self.predicted_q_value = tf.placeholder(tf.float32, [None, 1])

        # Define loss and optimization Op
        
        self.loss = tf.reduce_mean(tf.square(tf.subtract(self.predicted_q_value,self.out)))
        self.optimize = tf.train.AdamOptimizer(self.learning_rate).minimize(self.loss)

        # Get the gradient of the net w.r.t. the action.
        # For each action in the minibatch (i.e., for each x in xs),
        # this will sum up the gradients of each critic output in the minibatch
        # w.r.t. that action. Each output is independent of all
        # actions except for one.
        self.action_grads = tf.gradients(self.out, self.action)

    def create_critic_network(self,cell,scope):
        
        # weights initialization
        w1_initial = np.random.normal(size=(self.s_dim,400)).astype(np.float32)
        w2_initial = np.random.normal(size=(400,300)).astype(np.float32)
        w2_action  = np.random.normal(size=(self.a_dim,300)).astype(np.float32)
        w3_initial = np.random.uniform(size=(300,1),low= -0.0003, high=0.0003 ).astype(np.float32)
        # Placeholders
        inputs = tf.placeholder(tf.float32, shape=[None, self.s_dim])
        action = tf.placeholder(tf.float32, shape=[None, self.a_dim])
        # Layer 1 contains only the inputs of the state
        w1 = tf.Variable(w1_initial)
        b1 = tf.Variable(tf.zeros([400]))
        z1 = tf.matmul(inputs,w1)+b1
        l1 = tf.nn.relu(z1)
        # Layer in this layer, the actions are merged as inputs
        w2_i = tf.Variable(w2_initial)
        w2_a = tf.Variable(w2_action)
        b2 = tf.Variable(tf.zeros([300]))
        z2 = tf.matmul(l1,w2_i)+ tf.matmul(action,w2_a)+ b2 
        l2 = tf.nn.relu(z2)
        # RNN
        # placeholder 
        trainLength = tf.placeholder(dtype=tf.int32, name = 'trainlengh')
        # net
        l2Flat = tf.reshape(slim.flatten(l2),[self.batch_size,trainLength,self.h_size])
        state_in = cell.zero_state(self.batch_size, tf.float32)
        rnn,rnn_state = tf.nn.dynamic_rnn(cell= cell,inputs=l2Flat, dtype=tf.float32,initial_state=state_in,scope=scope)
        rnn = tf.reshape(rnn,shape=[-1,self.h_size])
        #output layer
        w3 = tf.Variable(w3_initial)
        b3 = tf.Variable(tf.zeros([1]))
        out  = tf.matmul(rnn,w3)+b3 # linear activation
        self.saver = tf.train.Saver()
        return inputs, action, out, trainLength


        

    def create_normal_critic_network(self):
        
        # weights initialization
        w1_initial = np.random.normal(size=(self.s_dim,HIDDEN_1)).astype(np.float32)
        w2_initial = np.random.normal(size=(HIDDEN_1,HIDDEN_2)).astype(np.float32)
        w2_action  = np.random.normal(size=(self.a_dim,HIDDEN_2)).astype(np.float32)
        w3_initial = np.random.uniform(size=(HIDDEN_2,1),low= -0.0003, high=0.0003 ).astype(np.float32)
        # Placeholders
        inputs = tf.placeholder(tf.float32, shape=[None, self.s_dim])
        action = tf.placeholder(tf.float32, shape=[None, self.a_dim])
        # Layer 1 contains only the inputs of the state
        w1 = tf.Variable(w1_initial)
        b1 = tf.Variable(tf.zeros([HIDDEN_1]))
        z1 = tf.matmul(inputs,w1)+b1
        l1 = tf.nn.relu(z1)
        # Layer in this layer, the actions are merged as inputs
        w2_i = tf.Variable(w2_initial)
        w2_a = tf.Variable(w2_action)
        b2 = tf.Variable(tf.zeros([HIDDEN_2]))
        z2 = tf.matmul(l1,w2_i)+ tf.matmul(action,w2_a)+ b2 
        l2 = tf.nn.relu(z2)
        #output layer
        w3 = tf.Variable(w3_initial)
        b3 = tf.Variable(tf.zeros([1]))
        out  = tf.matmul(l2,w3)+b3 # linear activation
        self.saver = tf.train.Saver()
        return inputs, action, out

    

      
    def train(self, inputs, action, predicted_q_value, trace_length):
        return self.sess.run([self.out, self.optimize], feed_dict={
            self.inputs: inputs,
            self.action: action,
            self.predicted_q_value: predicted_q_value,
            self.trainLength: trace_length
        })

    def predict(self, inputs, action, trace_length):
        return self.sess.run(self.out, feed_dict={
            self.inputs: inputs,
            self.action: action,
            self.trainLength: trace_length
        })

    def predict_target(self, inputs, action, trace_length):
        return self.sess.run(self.target_out, feed_dict={
            self.target_inputs: inputs,
            self.target_action: action,
            self.target_trainLength: trace_length
        })

    def action_gradients(self, inputs, actions, trace_length):
        return self.sess.run(self.action_grads, feed_dict={
            self.inputs: inputs,
            self.action: actions,
            self.trainLength: trace_length
        })

    def update_target_network(self):
        self.sess.run(self.update_target_network_params)
    
    def save_critic(self):
        self.saver.save(self.sess,'critic_model.ckpt')
        #saver.save(self.sess,'actor_model.ckpt')
        print("Model saved in file:")

    
    def recover_critic(self):
        self.saver.restore(self.sess,'critic_model.ckpt')
        #saver.restore(self.sess,'critic_model.ckpt')
    