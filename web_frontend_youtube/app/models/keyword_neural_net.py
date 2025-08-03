import numpy as np
import sqlite3
import pickle
import os
import time
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Tuple, Optional

class KeywordNeuralNet:
    """
    Lightweight neural network for learning keyword relationships and user preferences.
    Uses TF-IDF embeddings with a simple feedforward network for preference prediction.
    """
    
    def __init__(self, embedding_dim=100, hidden_dim=64, learning_rate=0.01):
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.learning_rate = learning_rate
        
        # TF-IDF vectorizer for keyword embeddings
        self.vectorizer = TfidfVectorizer(
            max_features=embedding_dim,
            stop_words='english',
            ngram_range=(1, 2),  # Include bigrams
            min_df=2,  # Ignore terms that appear in less than 2 documents
            max_df=0.8  # Ignore terms that appear in more than 80% of documents
        )
        
        # Neural network weights (will be initialized after first training)
        self.W1 = None  # Input to hidden layer
        self.b1 = None  # Hidden layer bias
        self.W2 = None  # Hidden to output layer
        self.b2 = None  # Output layer bias
        
        # Training data storage
        self.training_texts = []
        self.training_labels = []
        
        # Model state
        self.is_trained = False
        self.last_training_time = 0
        
    def _sigmoid(self, x):
        """Sigmoid activation function with numerical stability"""
        return np.where(x >= 0, 
                       1 / (1 + np.exp(-x)), 
                       np.exp(x) / (1 + np.exp(x)))
    
    def _sigmoid_derivative(self, x):
        """Derivative of sigmoid function"""
        s = self._sigmoid(x)
        return s * (1 - s)
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better feature extraction"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _initialize_weights(self, input_dim: int):
        """Initialize neural network weights using Xavier initialization"""
        # Xavier initialization for better convergence
        self.W1 = np.random.randn(input_dim, self.hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, self.hidden_dim))
        self.W2 = np.random.randn(self.hidden_dim, 1) * np.sqrt(2.0 / self.hidden_dim)
        self.b2 = np.zeros((1, 1))
    
    def _forward_pass(self, X):
        """Forward pass through the network"""
        # Hidden layer
        z1 = np.dot(X, self.W1) + self.b1
        a1 = self._sigmoid(z1)
        
        # Output layer
        z2 = np.dot(a1, self.W2) + self.b2
        a2 = self._sigmoid(z2)
        
        return z1, a1, z2, a2
    
    def _backward_pass(self, X, y, z1, a1, z2, a2):
        """Backward pass (backpropagation)"""
        m = X.shape[0]
        
        # Output layer gradients
        dz2 = a2 - y.reshape(-1, 1)
        dW2 = (1/m) * np.dot(a1.T, dz2)
        db2 = (1/m) * np.sum(dz2, axis=0, keepdims=True)
        
        # Hidden layer gradients
        dz1 = np.dot(dz2, self.W2.T) * self._sigmoid_derivative(z1)
        dW1 = (1/m) * np.dot(X.T, dz1)
        db1 = (1/m) * np.sum(dz1, axis=0, keepdims=True)
        
        return dW1, db1, dW2, db2
    
    def add_training_data(self, text: str, preference_score: float):
        """Add training data (video title and user preference)"""
        processed_text = self._preprocess_text(text)
        self.training_texts.append(processed_text)
        
        # Normalize preference score to [0, 1] range
        # Positive scores become > 0.5, negative scores become < 0.5
        normalized_score = 1 / (1 + np.exp(-preference_score))
        self.training_labels.append(normalized_score)
    
    def train(self, epochs=100, batch_size=32, validation_split=0.2):
        """Train the neural network on collected data"""
        if len(self.training_texts) < 10:
            print("Not enough training data (need at least 10 samples)")
            return False
        
        try:
            # Fit TF-IDF vectorizer and transform texts
            X = self.vectorizer.fit_transform(self.training_texts).toarray()
            y = np.array(self.training_labels)
            
            # Initialize weights if not done yet
            if self.W1 is None:
                self._initialize_weights(X.shape[1])
            
            # Split data for validation
            n_samples = X.shape[0]
            n_val = int(n_samples * validation_split)
            indices = np.random.permutation(n_samples)
            
            X_train, X_val = X[indices[n_val:]], X[indices[:n_val]]
            y_train, y_val = y[indices[n_val:]], y[indices[:n_val]]
            
            # Training loop
            train_losses = []
            val_losses = []
            
            for epoch in range(epochs):
                # Mini-batch training
                n_batches = max(1, len(X_train) // batch_size)
                epoch_loss = 0
                
                for i in range(n_batches):
                    start_idx = i * batch_size
                    end_idx = min((i + 1) * batch_size, len(X_train))
                    
                    X_batch = X_train[start_idx:end_idx]
                    y_batch = y_train[start_idx:end_idx]
                    
                    # Forward pass
                    z1, a1, z2, a2 = self._forward_pass(X_batch)
                    
                    # Compute loss (binary cross-entropy)
                    loss = -np.mean(y_batch * np.log(a2.flatten() + 1e-8) + 
                                  (1 - y_batch) * np.log(1 - a2.flatten() + 1e-8))
                    epoch_loss += loss
                    
                    # Backward pass
                    dW1, db1, dW2, db2 = self._backward_pass(X_batch, y_batch, z1, a1, z2, a2)
                    
                    # Update weights
                    self.W1 -= self.learning_rate * dW1
                    self.b1 -= self.learning_rate * db1
                    self.W2 -= self.learning_rate * dW2
                    self.b2 -= self.learning_rate * db2
                
                avg_train_loss = epoch_loss / n_batches
                train_losses.append(avg_train_loss)
                
                # Validation loss
                if len(X_val) > 0:
                    _, _, _, val_pred = self._forward_pass(X_val)
                    val_loss = -np.mean(y_val * np.log(val_pred.flatten() + 1e-8) + 
                                      (1 - y_val) * np.log(1 - val_pred.flatten() + 1e-8))
                    val_losses.append(val_loss)
                
                # Print progress every 20 epochs
                if (epoch + 1) % 20 == 0:
                    if len(X_val) > 0:
                        print(f"Epoch {epoch+1}/{epochs}, Train Loss: {avg_train_loss:.4f}, Val Loss: {val_loss:.4f}")
                    else:
                        print(f"Epoch {epoch+1}/{epochs}, Train Loss: {avg_train_loss:.4f}")
            
            self.is_trained = True
            self.last_training_time = time.time()
            
            print(f"Training completed! Final train loss: {train_losses[-1]:.4f}")
            if val_losses:
                print(f"Final validation loss: {val_losses[-1]:.4f}")
            
            return True
            
        except Exception as e:
            print(f"Training failed: {e}")
            return False
    
    def predict_preference(self, text: str) -> float:
        """Predict user preference for a given text"""
        if not self.is_trained:
            return 0.5  # Neutral preference if not trained
        
        try:
            processed_text = self._preprocess_text(text)
            X = self.vectorizer.transform([processed_text]).toarray()
            
            if X.shape[1] == 0:  # No features extracted
                return 0.5
            
            _, _, _, prediction = self._forward_pass(X)
            
            # Convert back to preference score range
            # 0.5 -> 0 (neutral), >0.5 -> positive, <0.5 -> negative
            preference_score = (prediction[0, 0] - 0.5) * 4  # Scale to roughly [-2, 2]
            
            return float(preference_score)
            
        except Exception as e:
            print(f"Prediction failed: {e}")
            return 0.5
    
    def get_keyword_similarities(self, text: str, top_k=10) -> List[Tuple[str, float]]:
        """Get most similar keywords/phrases to the input text"""
        if not self.is_trained:
            return []
        
        try:
            processed_text = self._preprocess_text(text)
            text_vector = self.vectorizer.transform([processed_text]).toarray()
            
            if text_vector.shape[1] == 0:
                return []
            
            # Get feature names (keywords)
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Calculate similarities with all features
            similarities = []
            for i, feature in enumerate(feature_names):
                if text_vector[0, i] > 0:  # Only consider features present in the text
                    feature_vector = np.zeros_like(text_vector)
                    feature_vector[0, i] = 1
                    
                    similarity = cosine_similarity(text_vector, feature_vector)[0, 0]
                    similarities.append((feature, similarity))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            print(f"Similarity calculation failed: {e}")
            return []
    
    def save_model(self, filepath: str):
        """Save the trained model to disk"""
        if not self.is_trained:
            print("Model not trained yet, nothing to save")
            return False
        
        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'W1': self.W1,
                'b1': self.b1,
                'W2': self.W2,
                'b2': self.b2,
                'embedding_dim': self.embedding_dim,
                'hidden_dim': self.hidden_dim,
                'learning_rate': self.learning_rate,
                'is_trained': self.is_trained,
                'last_training_time': self.last_training_time,
                'training_texts': self.training_texts,
                'training_labels': self.training_labels
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            print(f"Model saved to {filepath}")
            return True
            
        except Exception as e:
            print(f"Failed to save model: {e}")
            return False
    
    def load_model(self, filepath: str):
        """Load a trained model from disk"""
        if not os.path.exists(filepath):
            print(f"Model file not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.vectorizer = model_data['vectorizer']
            self.W1 = model_data['W1']
            self.b1 = model_data['b1']
            self.W2 = model_data['W2']
            self.b2 = model_data['b2']
            self.embedding_dim = model_data['embedding_dim']
            self.hidden_dim = model_data['hidden_dim']
            self.learning_rate = model_data['learning_rate']
            self.is_trained = model_data['is_trained']
            self.last_training_time = model_data['last_training_time']
            self.training_texts = model_data.get('training_texts', [])
            self.training_labels = model_data.get('training_labels', [])
            
            print(f"Model loaded from {filepath}")
            return True
            
        except Exception as e:
            print(f"Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        return {
            'is_trained': self.is_trained,
            'training_samples': len(self.training_texts),
            'embedding_dim': self.embedding_dim,
            'hidden_dim': self.hidden_dim,
            'learning_rate': self.learning_rate,
            'last_training_time': self.last_training_time,
            'vocabulary_size': len(self.vectorizer.get_feature_names_out()) if self.is_trained else 0
        }

class NeuralRecommendationEngine:
    """
    Enhanced recommendation engine that uses neural networks for keyword analysis
    """
    
    def __init__(self, db_path: str, model_path: str = None):
        self.db_path = db_path
        self.model_path = model_path or os.path.join(os.path.dirname(db_path), "keyword_model.pkl")
        
        # Initialize neural network
        self.neural_net = KeywordNeuralNet()
        
        # Try to load existing model
        if os.path.exists(self.model_path):
            self.neural_net.load_model(self.model_path)
        
        # Track when we last retrained
        self.last_retrain_time = 0
        self.retrain_interval = 3600  # Retrain every hour if new data available
    
    def _should_retrain(self) -> bool:
        """Check if we should retrain the model"""
        if not self.neural_net.is_trained:
            return True
        
        # Check if enough time has passed
        if time.time() - self.last_retrain_time < self.retrain_interval:
            return False
        
        # Check if we have new data since last training
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_interactions 
                WHERE timestamp > ?
            """, (self.neural_net.last_training_time,))
            
            new_interactions = cursor.fetchone()[0]
            conn.close()
            
            return new_interactions > 10  # Retrain if we have 10+ new interactions
            
        except Exception as e:
            print(f"Error checking for new data: {e}")
            return False
    
    def _collect_training_data(self):
        """Collect training data from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all interactions with video titles
            cursor.execute("""
                SELECT v.title, ui.interaction_type, ui.interaction_subtype, ui.timestamp
                FROM user_interactions ui
                JOIN videos v ON ui.video_id = v.video_id
                ORDER BY ui.timestamp DESC
            """)
            
            interactions = cursor.fetchall()
            
            # Clear previous training data
            self.neural_net.training_texts = []
            self.neural_net.training_labels = []
            
            # Convert interactions to training data
            for title, interaction_type, interaction_subtype, timestamp in interactions:
                # Calculate preference score based on interaction
                if interaction_type == 'starred':
                    preference_score = 2.0  # High positive preference
                elif interaction_type == 'disliked':
                    preference_score = -2.0  # High negative preference
                elif interaction_type == 'watched':
                    if interaction_subtype == 'clicked':
                        preference_score = 1.0  # Positive preference
                    else:  # 'marked'
                        preference_score = 0.3  # Slight positive preference
                else:
                    continue  # Skip unknown interaction types
                
                # Add recency weighting (more recent interactions are more important)
                days_ago = (time.time() - timestamp) / (24 * 3600)
                recency_weight = max(0.1, 1.0 - (days_ago / 90))  # Decay over 90 days
                weighted_score = preference_score * recency_weight
                
                self.neural_net.add_training_data(title, weighted_score)
            
            conn.close()
            
            print(f"Collected {len(self.neural_net.training_texts)} training samples")
            return True
            
        except Exception as e:
            print(f"Error collecting training data: {e}")
            return False
    
    def train_model(self, force_retrain=False):
        """Train or retrain the neural network model"""
        if not force_retrain and not self._should_retrain():
            return True
        
        print("Training neural network model...")
        
        # Collect training data
        if not self._collect_training_data():
            return False
        
        # Train the model
        success = self.neural_net.train(epochs=100, batch_size=16)
        
        if success:
            # Save the trained model
            self.neural_net.save_model(self.model_path)
            self.last_retrain_time = time.time()
            print("Neural network training completed successfully!")
        else:
            print("Neural network training failed!")
        
        return success
    
    def get_neural_score(self, title: str) -> float:
        """Get neural network preference score for a video title"""
        # Ensure model is trained
        if not self.neural_net.is_trained:
            self.train_model()
        
        if not self.neural_net.is_trained:
            return 0.0  # Fallback if training failed
        
        return self.neural_net.predict_preference(title)
    
    def get_keyword_insights(self, title: str) -> Dict:
        """Get insights about keywords in the title"""
        if not self.neural_net.is_trained:
            return {}
        
        similarities = self.neural_net.get_keyword_similarities(title, top_k=5)
        preference_score = self.neural_net.predict_preference(title)
        
        return {
            'neural_preference_score': preference_score,
            'similar_keywords': similarities,
            'model_info': self.neural_net.get_model_info()
        }
    
    def get_model_stats(self) -> Dict:
        """Get statistics about the neural network model"""
        return self.neural_net.get_model_info()

# Global instance (will be initialized by the main recommendation engine)
neural_engine = None