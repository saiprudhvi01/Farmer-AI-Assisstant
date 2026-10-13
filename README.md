# 🌱 FarmMitra - AI-Powered Farming Assistant

<div align="center">

![FarmMitra Logo](https://img.shields.io/badge/FarmMitra-AI%20Assistant-green?style=for-the-badge&logo=agriculture)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0+-white?style=for-the-badge&logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A multilingual AI-powered farming assistant with voice interaction, image analysis, weather intelligence, and decision support for farmers.**

[Live Demo](#) • [Report Bug](#) • [Request Feature](#)

</div>

---

## 📸 Screenshots

<!-- Add your screenshots here -->
<div align="center">
  <img src="https://via.placeholder.com/800x400/1f5a3a/fff6e0?text=Home+Page" alt="Home Page" width="45%">
  <img src="https://via.placeholder.com/800x400/f2a43a/fff6e0?text=Leaf+Analysis" alt="Leaf Analysis" width="45%">
</div>

<div align="center">
  <img src="https://via.placeholder.com/800x400/2f5d8a/fff6e0?text=Weather+Dashboard" alt="Weather Dashboard" width="45%">
  <img src="https://via.placeholder.com/800x400/d63c3c/fff6e0?text=Crop+Health" alt="Crop Health" width="45%">
</div>

---

## ✨ Features

### 🌍 Multilingual Support
- **8 Indian Languages**: English, Telugu, Hindi, Tamil, Kannada, Marathi, Bengali, Gujarati
- **Voice Input/Output**: Speech-to-text and text-to-speech in all supported languages
- **AI Translation**: Automatic translation using Google Translate API

### 🤖 AI-Powered Analysis
- **Leaf Disease Detection**: Upload leaf photos for AI-powered disease analysis using Gemini Vision API
- **Crop Health Assessment**: Overall crop health evaluation through image analysis
- **Smart Recommendations**: Explainable AI with What/When/Why context for all recommendations

### 🌦️ Weather Intelligence
- **Real-time Weather**: Live temperature, humidity, and precipitation data
- **7-Day Forecast**: Extended weather predictions for better planning
- **Weather Alerts**: Automatic alerts for rain and extreme weather conditions

### 💧 Smart Irrigation
- **Irrigation Advisory**: Smart recommendations based on weather conditions and crop needs
- **Water Conservation**: Optimized watering schedules to save resources

### 📊 Crop Management
- **Crop Setup**: Easy configuration of crop details, variety, sowing date, location
- **Farm Details**: Track farm size, soil type, and irrigation method
- **Maturity Tracking**: Progress indicators and harvest timing estimates

### 🎤 Voice Interaction
- **Voice Questions**: Ask farming questions using speech input
- **Audio Responses**: Get AI responses as audio in your language
- **Hands-free Operation**: Perfect for farmers in the field

### 🔄 Continuous Improvement
- **Feedback System**: User feedback collection on analysis results
- **Re-analysis**: Ability to re-analyze images with updated AI models
- **Learning**: Improves accuracy over time with user feedback

---

## 🚀 Deployment

### Deploy on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Step-by-step deployment:**

1. **Fork this repository**
   ```bash
   git clone https://github.com/saiprudhvi01/Farmer-AI-Assisstant.git
   cd Farmer-AI-Assisstant
   ```

2. **Create a Render account** at [render.com](https://render.com)

3. **Create a new Web Service**
   - Connect your GitHub repository
   - Select the `Farmer-AI-Assisstant` repository
   - Configure build settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python app.py`

4. **Add Environment Variables** in Render dashboard:
   ```
   FLASK_SECRET_KEY=your-secret-key-here
   GEMINI_API_KEY=your-gemini-api-key-here
   FLASK_DEBUG=0
   PORT=10000
   ```

5. **Deploy** - Render will automatically detect the port and deploy your app

### Manual Deployment

```bash
# Clone the repository
git clone https://github.com/saiprudhvi01/Farmer-AI-Assisstant.git
cd Farmer-AI-Assisstant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY

# Run the application
python app.py
```

---

## 🛠️ Local Development

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

```powershell
# Clone the repository
git clone https://github.com/saiprudhvi01/Farmer-AI-Assisstant.git
cd Farmer-AI-Assisstant

# Create virtual environment
py -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY

# Run the application
python app.py
```

Open http://127.0.0.1:5000 in your browser.

---

## 📁 Project Structure

```
FarmMitra/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── static/               # Static files (CSS, JS, images)
│   ├── style.css         # Main stylesheet
│   ├── guided_form.js    # Form JavaScript
│   └── background.png   # Background images
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── home.html         # Home page
│   ├── feature.html      # Feature pages
│   ├── guided_form.html  # Guided form
│   └── loading.html      # Loading page
├── uploads/              # User uploaded images
└── bgimages/            # Background images (optional)
```

---

## 🔧 Environment Variables

Create a `.env` file in the project root:

```env
FLASK_SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key-here
FLASK_DEBUG=1  # Set to 0 for production
```

### Getting API Keys

- **Gemini API Key**: [Get one here](https://makersuite.google.com/app/apikey)
- **Flask Secret Key**: Generate a random string using `python -c "import secrets; print(secrets.token_hex(32))"`

---

## 🗄️ Database

The app uses SQLite (`farmmitra.db`) with tables for:
- **Farm details**: Crop information, location, soil type
- **Analysis results**: Image analysis and AI responses
- **User feedback**: Feedback on analysis results

Database is automatically created on first run.

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/speech-to-text` | POST | Convert speech audio to text |
| `/api/text-to-speech` | POST | Convert text to speech audio |
| `/api/weather` | GET | Get weather data for farm location |
| `/api/analyze` | POST | Analyze crop images with Gemini |
| `/api/irrigation` | GET | Get irrigation advice |
| `/api/maturity` | GET | Get crop maturity estimate |
| `/api/ask` | POST | Ask farming questions with Gemini |
| `/api/decision/<feature>` | GET | Get explainable decision context |
| `/api/feedback` | POST | Submit feedback on analysis |
| `/api/reanalyze/<id>` | POST | Re-analyze existing images |

---

## 🌐 Language Support

All input and output (text and audio) are automatically translated to the selected language:

| Language | Code | Native Name |
|----------|------|-------------|
| English | `en` | English |
| Telugu | `te` | తెలుగు |
| Hindi | `hi` | हिंदी |
| Tamil | `ta` | தமிழ் |
| Kannada | `kn` | ಕನ್ನಡ |
| Marathi | `mr` | मराठी |
| Bengali | `bn` | বাংলা |
| Gujarati | `gu` | ગુજરાતી |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Google Gemini AI](https://ai.google.dev/) for AI capabilities
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Google Translate API](https://cloud.google.com/translate) for multilingual support
- [OpenWeatherMap](https://openweathermap.org/) for weather data

---

## 📧 Contact

- **Project Link**: [https://github.com/saiprudhvi01/Farmer-AI-Assisstant](https://github.com/saiprudhvi01/Farmer-AI-Assisstant)
- **Issues**: [https://github.com/saiprudhvi01/Farmer-AI-Assisstant/issues](https://github.com/saiprudhvi01/Farmer-AI-Assisstant/issues)

---

<div align="center">

**Made with ❤️ for Farmers**

[⬆ Back to Top](#-farmmitra---ai-powered-farming-assistant)

</div>
