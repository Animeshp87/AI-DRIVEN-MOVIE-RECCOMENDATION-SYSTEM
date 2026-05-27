# 🎬 Smart Movie Recommender

A modern web application that provides AI-powered movie recommendations using Flask, HTML, CSS, and JavaScript.

## Features

- 🎯 **Smart Recommendations**: Get personalized movie recommendations based on your selection
- 🎨 **Beautiful UI**: Modern, responsive design with gradient backgrounds and smooth animations
- 📱 **Mobile Friendly**: Fully responsive design that works on all devices
- 🖼️ **Dynamic Posters**: Automatically generated movie posters with gradient backgrounds
- ⚡ **Fast Performance**: Optimized for quick loading and smooth interactions

## Prerequisites

Make sure you have the following installed:
- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. **Clone or download the project files**

2. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure you have the required data files**:
   - `movies_list.pkl` - Contains the movie dataset
   - `similarity.pkl` - Contains the similarity matrix for recommendations

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app_flask.py
   ```

2. **Open your web browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Select a movie** from the dropdown menu and click "🎯 Get Recommendations"

## Project Structure

```
├── app_flask.py          # Flask backend application
├── templates/
│   └── index.html        # Main HTML template with CSS and JavaScript
├── movie_posters/        # Generated movie posters (created automatically)
├── requirements.txt      # Python dependencies
├── movies_list.pkl       # Movie dataset
├── similarity.pkl        # Similarity matrix
└── README.md            # This file
```

## How It Works

1. **Backend (Flask)**:
   - Loads movie data from pickle files
   - Handles recommendation logic using similarity matrix
   - Generates dynamic movie posters using PIL
   - Serves the web interface and API endpoints

2. **Frontend (HTML/CSS/JavaScript)**:
   - Modern, responsive design with gradient backgrounds
   - Interactive movie selection dropdown
   - AJAX calls to get recommendations
   - Smooth animations and hover effects
   - Mobile-friendly layout

3. **Recommendation System**:
   - Uses content-based filtering
   - Calculates similarity between movies
   - Returns top 5 most similar movies
   - Shows match scores as percentages

## Customization

### Styling
You can customize the appearance by modifying the CSS in `templates/index.html`:
- Change colors in the gradient backgrounds
- Modify card styles and animations
- Adjust responsive breakpoints

### Functionality
- Modify the recommendation algorithm in `app_flask.py`
- Add new features like user ratings or reviews
- Integrate with external movie APIs

## Troubleshooting

### Common Issues

1. **"Movie data not loaded" error**:
   - Ensure `movies_list.pkl` and `similarity.pkl` files are in the project directory
   - Check file permissions

2. **Port already in use**:
   - Change the port in `app_flask.py` (line with `app.run()`)
   - Or kill the process using the current port

3. **Missing dependencies**:
   - Run `pip install -r requirements.txt` again
   - Check Python version compatibility

### Performance Tips

- The first run may be slower as it generates movie posters
- Subsequent runs will be faster as posters are cached
- For production, consider using a proper web server like Gunicorn

## Technologies Used

- **Backend**: Flask, Python, Pandas, NumPy, PIL
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Data**: Pickle files for movie data and similarity matrix
- **Styling**: Custom CSS with gradients, animations, and responsive design

## License

This project is open source and available under the MIT License.

---

**Enjoy discovering your next favorite movie! 🎬✨** 