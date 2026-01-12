This project is a web application that predicts which character from The Big Bang Theory is most likely to say a specific line of dialogue. It uses natural language processing and vector similarity search to analyze the input text and match it against a database of lines from the show.

## How to Use

# Open the Application: Navigate to the hosted frontend URL.

# Enter Text: In the main input box, type a sentence, quote, or phrase you want to test.

# Submit: Click the "Post" button.

#View Result: The application will process your text. A "reply" will appear in the feed from the character the model predicts would say that line, complete with their name and profile picture.

## How This Project Was Made
This application operates as a full-stack system utilizing a retrieval-based machine learning approach.

# 1. Data Processing

# The core dataset consists of dialogue transcripts from 10 seasons of The Big Bang Theory. These scripts were cleaned and processed to associate every line of dialogue with the character who spoke it. The data pipeline handles text normalization and filtering to ensure high-quality matching.

# 2. Machine Learning & Natural Language Processing

# Instead of a generative LLM (Large Language Model), this project uses a retrieval-augmented approach:

# Embeddings: The system uses Sentence Transformers to convert lines of dialogue into dense vector embeddings. This allows the computer to understand the semantic meaning of the text rather than just matching keywords.

# Vector Database: These embeddings are stored in a FAISS (Facebook AI Similarity Search) index, allowing for extremely fast similarity searches across thousands of lines of dialogue.

# Prediction Logic: When a user inputs text, the system converts it into a vector and queries the FAISS index to find the most semantically similar lines from the show. It then uses Reciprocal Rank Fusion (RRF) to score the results and determine which character is statistically most likely to say that line based on the retrieved context.

# 3. Backend Architecture

# The backend is built with FastAPI. It exposes endpoints that:

# Accept user queries.

# Run the prediction logic.

# Return the predicted character, confidence score, and metadata.

# Manage character assets (images) by scraping or using cached local files when necessary.

# 4. Frontend Architecture

# The frontend is built with Vanilla JavaScript, HTML, and CSS. It does not use heavy frameworks like React or Vue, keeping it lightweight. The interface is designed to mimic a social media feed, dynamically rendering "tweets" and "replies" using the DOM API.

# 5. Deployment

# Backend: Packaged into a Docker container (defined in Dockerfile) and deployed to a cloud hosting platform (e.g., Hugging Face Spaces).

# Frontend: Deployed as a static site (e.g., Vercel) that communicates with the backend API via HTTP requests.