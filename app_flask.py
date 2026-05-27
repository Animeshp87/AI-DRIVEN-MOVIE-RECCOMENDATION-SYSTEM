from flask import Flask, render_template, request, jsonify, send_file
import pickle
import pandas as pd
import os
from pathlib import Path
import base64
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import textwrap
import random
import numpy as np

app = Flask(__name__)

# Create directories for assets if they don't exist
for dir_name in ['movie_posters', 'assets', 'static']:
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

# Predefined color schemes for posters
COLOR_SCHEMES = [
    [(41, 128, 185), (52, 152, 219)],  # Blue
    [(155, 89, 182), (142, 68, 173)],  # Purple
    [(46, 204, 113), (39, 174, 96)],   # Green
    [(241, 196, 15), (243, 156, 18)],  # Yellow
    [(231, 76, 60), (192, 57, 43)],    # Red
]

def create_gradient_background(width, height):
    # Randomly choose a color scheme
    color1, color2 = random.choice(COLOR_SCHEMES)
    
    # Create a gradient array
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    X, Y = np.meshgrid(x, y)
    gradient = (X + Y) / 2
    
    # Create the gradient image
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(3):
        img[:, :, i] = np.interp(gradient, [0, 1], [color1[i], color2[i]])
    
    return Image.fromarray(img)

def create_sample_poster(movie_title, movie_id):
    try:
        # Check if we already have this poster
        poster_path = f'movie_posters/movie_{movie_id}.png'
        if os.path.exists(poster_path):
            try:
                with Image.open(poster_path) as img:
                    # Verify the image can be opened
                    img.verify()
                return poster_path
            except:
                # If image is corrupted, remove it and create new one
                os.remove(poster_path)
        
        # Create poster dimensions
        width, height = 500, 750
        
        # Create gradient background
        img = create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)
        
        # Try multiple font sizes for title
        font_size = 60
        font = None
        wrapped_text = movie_title
        
        # Try different font sizes until the text fits
        while font_size > 20:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
                wrapped_text = textwrap.fill(movie_title, width=int(20 * 40/font_size))
                text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                if text_width < width - 60:
                    break
            except:
                pass
            font_size -= 5
        
        if font is None:
            font = ImageFont.load_default()
        
        # Calculate text position
        text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Add decorative elements
        # Top banner
        draw.rectangle([0, 0, width, 100], fill=(0, 0, 0, 128))
        # Bottom banner
        draw.rectangle([0, height-100, width, height], fill=(0, 0, 0, 128))
        
        # Add movie title with shadow effect
        shadow_offset = 3
        draw.text((x + shadow_offset, y + shadow_offset), wrapped_text, fill=(0, 0, 0, 128), font=font)
        draw.text((x, y), wrapped_text, fill='white', font=font)
        
        # Add decorative lines
        line_color = 'white'
        line_width = 3
        # Top lines
        draw.line([(30, 30), (width-30, 30)], fill=line_color, width=line_width)
        draw.line([(30, 40), (width-30, 40)], fill=line_color, width=line_width)
        # Bottom lines
        draw.line([(30, height-30), (width-30, height-30)], fill=line_color, width=line_width)
        draw.line([(30, height-40), (width-30, height-40)], fill=line_color, width=line_width)
        
        # Add movie info
        small_font_size = 30
        try:
            small_font = ImageFont.truetype("arial.ttf", small_font_size)
        except:
            small_font = ImageFont.load_default()
            
        # Add "MOVIE ID" at top
        id_text = f"MOVIE ID: {movie_id}"
        id_bbox = draw.textbbox((0, 0), id_text, font=small_font)
        id_width = id_bbox[2] - id_bbox[0]
        draw.text(((width - id_width) // 2, 35), id_text, fill='white', font=small_font)
        
        # Add year at bottom
        year_text = f"© {datetime.now().year}"
        year_bbox = draw.textbbox((0, 0), year_text, font=small_font)
        year_width = year_bbox[2] - year_bbox[0]
        draw.text(((width - year_width) // 2, height-60), year_text, fill='white', font=small_font)
        
        # Save with high quality
        img.save(poster_path, format='PNG', quality=95, optimize=True)
        return poster_path
    except Exception as e:
        print(f"Error creating poster: {str(e)}")
        # Create a simple error poster
        error_img = Image.new('RGB', (500, 750), (47, 53, 66))
        error_draw = ImageDraw.Draw(error_img)
        error_draw.text((100, 375), "Error creating poster", fill='white')
        error_img.save(poster_path)
        return poster_path

# Load movie data
def load_movie_data():
    try:
        movies = pickle.load(open("movies_list.pkl", 'rb'))
        similarity = pickle.load(open("similarity.pkl", 'rb'))
        return movies, similarity
    except Exception as e:
        print(f"Failed to load movie data. Please check if the data files exist. Error: {str(e)}")
        return None, None

# Load data globally
movies, similarity = load_movie_data()

def recommend(movie):
    try:
        index = movies[movies['title'] == movie].index[0]
        distance = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda vector: vector[1])
        recommend_movie = []
        recommend_posters = []
        similarity_scores = []
        
        for i in distance[1:6]:
            movie_id = movies.iloc[i[0]].id
            movie_title = movies.iloc[i[0]].title
            recommend_movie.append(movie_title)
            poster_path = create_sample_poster(movie_title, movie_id)
            recommend_posters.append(poster_path)
            similarity_scores.append(round(i[1] * 100, 1))  # Convert to percentage
            
        return recommend_movie, recommend_posters, similarity_scores
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return [], [], []

@app.route('/')
def index():
    if movies is None:
        return "Error: Movie data not loaded", 500
    
    movies_list = movies['title'].values.tolist()
    return render_template('index.html', movies=movies_list)

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    if movies is None:
        return jsonify({'error': 'Movie data not loaded'}), 500
    
    data = request.get_json()
    selected_movie = data.get('movie')
    
    if not selected_movie:
        return jsonify({'error': 'No movie selected'}), 400
    
    movie_names, movie_posters, similarity_scores = recommend(selected_movie)
    
    # Convert posters to base64 for frontend
    poster_data = []
    for poster_path in movie_posters:
        try:
            with open(poster_path, 'rb') as f:
                poster_bytes = f.read()
                poster_base64 = base64.b64encode(poster_bytes).decode('utf-8')
                poster_data.append(f"data:image/png;base64,{poster_base64}")
        except Exception as e:
            print(f"Error reading poster: {str(e)}")
            poster_data.append(None)
    
    recommendations = []
    for i, (name, poster, score) in enumerate(zip(movie_names, poster_data, similarity_scores), 1):
        recommendations.append({
            'id': i,
            'title': name,
            'poster': poster,
            'score': score
        })
    
    return jsonify({'recommendations': recommendations})

@app.route('/movie_posters/<path:filename>')
def serve_poster(filename):
    return send_file(f'movie_posters/{filename}')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 