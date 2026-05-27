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

# Create directories for assets if they don't exist
for dir_name in ['movie_posters', 'assets']:
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

def print_banner():
    print("=" * 80)
    print("🎬 SMART MOVIE RECOMMENDER 🎬")
    print("=" * 80)
    print("Discover your next favorite movie with our AI-powered recommendation system!")
    print("=" * 80)

def print_movie_list(movies_list, start_idx=0, count=10):
    """Print a paginated list of movies"""
    end_idx = min(start_idx + count, len(movies_list))
    print(f"\n📽️  Movies {start_idx + 1}-{end_idx} of {len(movies_list)}:")
    print("-" * 60)
    
    for i in range(start_idx, end_idx):
        print(f"{i+1:4d}. {movies_list[i]}")
    
    if end_idx < len(movies_list):
        print(f"\n... and {len(movies_list) - end_idx} more movies")
    
    print("-" * 60)

def main():
    print_banner()
    
    # Load data
    print("🔄 Loading movie data...")
    global movies, similarity
    movies, similarity = load_movie_data()
    
    if movies is None:
        print("❌ Error: Could not load movie data. Please check if movies_list.pkl and similarity.pkl exist.")
        return
    
    movies_list = movies['title'].values.tolist()
    print(f"✅ Loaded {len(movies_list)} movies successfully!")
    
    current_page = 0
    movies_per_page = 10
    
    while True:
        print("\n" + "=" * 80)
        print("🎯 MAIN MENU")
        print("=" * 80)
        print("1. 📽️  Browse Movies")
        print("2. 🔍 Search Movies")
        print("3. 🎯 Get Recommendations")
        print("4. 📁 View Generated Posters")
        print("5. ❌ Exit")
        print("=" * 80)
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            # Browse movies
            while True:
                print_movie_list(movies_list, current_page * movies_per_page, movies_per_page)
                
                print("\nNavigation:")
                print("n - Next page | p - Previous page | b - Back to main menu")
                nav = input("Enter navigation command: ").strip().lower()
                
                if nav == 'n':
                    if (current_page + 1) * movies_per_page < len(movies_list):
                        current_page += 1
                    else:
                        print("⚠️  Already at the last page!")
                elif nav == 'p':
                    if current_page > 0:
                        current_page -= 1
                    else:
                        print("⚠️  Already at the first page!")
                elif nav == 'b':
                    break
                else:
                    print("❌ Invalid command!")
        
        elif choice == "2":
            # Search movies
            search_term = input("\n🔍 Enter movie name to search: ").strip().lower()
            if search_term:
                matching_movies = [movie for movie in movies_list if search_term in movie.lower()]
                if matching_movies:
                    print(f"\n✅ Found {len(matching_movies)} matching movies:")
                    print("-" * 60)
                    for i, movie in enumerate(matching_movies[:20], 1):  # Show first 20 results
                        print(f"{i:2d}. {movie}")
                    if len(matching_movies) > 20:
                        print(f"... and {len(matching_movies) - 20} more results")
                else:
                    print("❌ No movies found matching your search term.")
            else:
                print("❌ Please enter a search term.")
        
        elif choice == "3":
            # Get recommendations
            print(f"\n🎯 RECOMMENDATION SYSTEM")
            print("=" * 60)
            print("Enter a movie name or number from the list:")
            
            # Show some popular movies as examples
            print("\n📋 Popular movies (examples):")
            example_movies = movies_list[:10]
            for i, movie in enumerate(example_movies, 1):
                print(f"{i:2d}. {movie}")
            
            movie_input = input("\nEnter movie name or number: ").strip()
            
            selected_movie = None
            
            # Check if input is a number
            if movie_input.isdigit():
                idx = int(movie_input) - 1
                if 0 <= idx < len(movies_list):
                    selected_movie = movies_list[idx]
            
            # If not a number, search for the movie
            if not selected_movie:
                matching_movies = [movie for movie in movies_list if movie_input.lower() in movie.lower()]
                if len(matching_movies) == 1:
                    selected_movie = matching_movies[0]
                elif len(matching_movies) > 1:
                    print(f"\n🔍 Multiple matches found:")
                    for i, movie in enumerate(matching_movies[:10], 1):
                        print(f"{i:2d}. {movie}")
                    if len(matching_movies) > 10:
                        print(f"... and {len(matching_movies) - 10} more")
                    
                    choice_num = input("Enter the number of your choice: ").strip()
                    if choice_num.isdigit():
                        idx = int(choice_num) - 1
                        if 0 <= idx < len(matching_movies):
                            selected_movie = matching_movies[idx]
            
            if selected_movie:
                print(f"\n🎬 Selected: {selected_movie}")
                print("🔄 Generating recommendations...")
                
                movie_names, movie_posters, similarity_scores = recommend(selected_movie)
                
                if movie_names:
                    print(f"\n🎯 TOP 5 RECOMMENDATIONS for '{selected_movie}':")
                    print("=" * 80)
                    
                    for i, (name, poster, score) in enumerate(zip(movie_names, movie_posters, similarity_scores), 1):
                        print(f"\n{i}. 🎬 {name}")
                        print(f"   📊 Match Score: {score}%")
                        print(f"   🖼️  Poster saved: {poster}")
                        print("-" * 60)
                    
                    print(f"\n✅ Generated {len(movie_posters)} movie posters in 'movie_posters/' folder!")
                else:
                    print("❌ No recommendations found.")
            else:
                print("❌ Movie not found. Please try again.")
        
        elif choice == "4":
            # View generated posters
            poster_dir = "movie_posters"
            if os.path.exists(poster_dir):
                posters = [f for f in os.listdir(poster_dir) if f.endswith('.png')]
                if posters:
                    print(f"\n📁 Generated Posters ({len(posters)} files):")
                    print("-" * 60)
                    for i, poster in enumerate(posters[:20], 1):  # Show first 20
                        print(f"{i:2d}. {poster}")
                    if len(posters) > 20:
                        print(f"... and {len(posters) - 20} more posters")
                    print(f"\n📂 Poster directory: {os.path.abspath(poster_dir)}")
                else:
                    print("📁 No posters generated yet. Get some recommendations first!")
            else:
                print("📁 Poster directory not found.")
        
        elif choice == "5":
            print("\n👋 Thank you for using Smart Movie Recommender!")
            print("🎬 Happy movie watching!")
            break
        
        else:
            print("❌ Invalid choice! Please enter 1-5.")

if __name__ == "__main__":
    main() 