import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
import io
import tempfile
import base64

from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Translation and AI
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    gTTS = None

import google.generativeai as genai
import requests

# PIL - explicitly import sub-modules so google-generativeai SDK can resolve them
import PIL
import PIL.Image
import PIL.PngImagePlugin
import PIL.JpegImagePlugin
import PIL.WebPImagePlugin
from PIL import Image

# ML disabled - using Gemini API only
ML_AVAILABLE = False

# Load environment variables
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "farmmitra.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")
genai.configure(api_key=GEMINI_API_KEY)

# Function to get a free model that supports generateContent
def get_available_model():
    try:
        models = genai.list_models()
        # Prioritize officially supported models for generateContent
        supported_models = [
            'models/gemini-2.5-flash',
            'models/gemini-2.5-flash-lite'
        ]
        for model in models:
            if model.name in supported_models and 'generateContent' in model.supported_generation_methods:
                return model.name
        # Fallback to any model that supports generateContent
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                return model.name
        return None
    except Exception as e:
        print(f"Error listing models: {e}")
        return None
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "farmmitra-local-demo-key")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

LANGUAGES = {
    "en": "English", "te": "తెలుగు", "hi": "हिन्दी", "ta": "தமிழ்",
    "kn": "ಕನ್ನಡ", "mr": "मराठी", "bn": "বাংলা", "gu": "ગુજરાતી",
}
TEXT = {
    "en": {"hello": "How can I help you today?", "leaf": "Check My Leaf", "health": "Check Crop Health", "water": "Watering Advice", "harvest": "Harvest Estimate", "ask": "Ask FarmMitra", "recommend": "Crop Recommendation", "today": "Today's weather", "need": "What do you need?", "listen": "Listening...", "speak": "Tap to speak", "stop": "Stop listening", "analyzing": "Analyzing...", "what": "What", "when": "When", "why": "Why", "feedback": "Was this helpful?", "yes": "Yes", "no": "No", "reanalyze": "Re-analyze",
          "step": "Step", "of": "of", "next": "Next", "back": "Back", "submit": "Submit", "cancel": "Cancel", "retry": "Retry", "loading": "Loading...", "checking": "Checking your crop health...", "getting_advice": "Getting watering advice...", "estimating": "Estimating harvest...", "please_answer": "Please answer this question to continue.", "invalid_value": "Please enter a valid value.", "value_required": "This field is required.", "checking_crop_health": "Checking your crop health...", "watering_recommendation": "Watering recommendation:", "recommended_amount": "Recommended amount:", "best_time": "Best time:", "reason": "Reason:", "next_action": "Next action:", "water_now": "Water now", "wait": "Wait", "irrigate_soon": "Irrigate soon", "do_not_irrigate": "Do not irrigate", "estimated_harvest": "Estimated harvest:", "expected_period": "Expected harvest period:", "main_factors": "Main factors:", "suggestion": "Suggestion:", "direct_answer": "Direct Answer", "what_you_should_do": "What You Should Do", "important_note": "Important Note", "leaf_status": "Leaf Status", "possible_problem": "Possible Problem", "recommended_actions": "Recommended Actions", "prevention": "Prevention", "confidence_limitations": "Confidence and Limitations",
          "q_soil_moisture": "What is the soil moisture level?", "q_soil_moisture_desc": "Enter the moisture percentage in your soil. Use a soil moisture meter or estimate based on how the soil feels.", "q_soil_ph": "What is the soil pH level?", "q_soil_ph_desc": "pH measures how acidic or alkaline your soil is. 7 is neutral. Most crops prefer 6.0 to 7.5.", "q_nitrogen": "What is the nitrogen level?", "q_nitrogen_desc": "Nitrogen helps leaves grow. Low means yellow leaves, adequate means green healthy leaves.", "q_phosphorus": "What is the phosphorus level?", "q_phosphorus_desc": "Phosphorus helps roots and seeds. Low means weak roots, adequate means strong roots.", "q_potassium": "What is the potassium level?", "q_potassium_desc": "Potassium helps overall plant health and disease resistance. Low means weak plants.", "q_ec": "What is the electrical conductivity (EC)?", "q_ec_desc": "EC measures salt in soil. High salt can harm plants. Low to moderate is usually good.", "q_issues": "Any problems with the crop?", "q_issues_desc": "Describe any issues you see like yellowing leaves, spots, wilting, or pests.", "q_growth_stage": "What is the crop growth stage?", "q_growth_stage_desc": "Select the current stage of your crop. Seedling is when plants are small. Vegetative is leaf growth. Flowering is when flowers appear. Fruiting is when fruits form. Maturity is near harvest time.",
          "q_crop_type": "What crop are you growing?", "q_crop_type_desc": "Select the type of crop from the list.", "q_planting_date": "When did you plant the crop?", "q_planting_date_desc": "Enter the date when you planted or sowed the seeds.", "q_plant_height": "What is the average plant height?", "q_plant_height_desc": "Measure the height of your plants in centimeters from ground to top.", "q_branches": "How many branches per plant?", "q_branches_desc": "Count the number of main branches on an average plant.", "q_fFruit_count": "How many fruits or bolls per plant?", "q_fruit_count_desc": "Count the number of fruits, pods, or cotton bolls on an average plant.", "q_fruit_size": "What is the average fruit size?", "q_fruit_size_desc": "Measure the size of an average fruit in centimeters.", "q_temperature": "What is the current temperature?", "q_temperature_desc": "Enter the current air temperature in degrees Celsius.", "q_humidity": "What is the humidity level?", "q_humidity_desc": "Enter the current humidity percentage.", "q_rainfall": "How much rainfall recently?", "q_rainfall_desc": "Enter total rainfall in millimeters over the last few days.", "q_npk": "What is the fertilizer/NPK level?", "q_npk_desc": "Low means you haven't applied much fertilizer. Adequate means you have applied enough.", "q_pest_severity": "How severe is pest or disease damage?", "q_pest_severity_desc": "Estimate the percentage of plants affected by pests or diseases. 0 means no damage, 100 means severe damage.",
          "seedling": "Seedling", "vegetative": "Vegetative growth", "flowering": "Flowering", "fruiting": "Fruiting", "maturity": "Maturity"},
    "te": {"hello": "ఈ రోజు మీకు ఎలా సహాయం చేయగలను?", "leaf": "ఆకును పరిశీలించండి", "health": "పంట ఆరోగ్యాన్ని చూడండి", "water": "నీటి సలహా", "harvest": "పంట కోత అంచనా", "ask": "ఫార్మ్‌మిత్రను అడగండి", "recommend": "పంట సిఫారసు", "today": "నేటి వాతావరణం", "need": "మీకు ఏమి కావాలి?", "listen": "వినిపిస్తోంది...", "speak": "మాట్లాడటానికి నొక్కండి", "stop": "వినిపించడం ఆపండి", "analyzing": "విశ్లేషిస్తోంది...", "what": "ఏమి", "when": "ఎప్పుడు", "why": "ఎందుకు", "feedback": "ఇది సహాయపడిందా?", "yes": "అవును", "no": "కాదు", "reanalyze": "మళ్ళీ విశ్లేషించండి",
          "step": "దశ", "of": "లో", "next": "తదుపరి", "back": "వెనుకకు", "submit": "సమర్పించండి", "cancel": "రద్దు చేయండి", "retry": "మళ్ళీ ప్రయత్నించండి", "loading": "లోడ్ అవుతోంది...", "checking": "మీ పంట ఆరోగ్యాన్ని పరిశీలిస్తోంది...", "getting_advice": "నీటి సలహా పొందుతోంది...", "estimating": "కోత అంచనా వేస్తోంది...", "please_answer": "కొనసాగించడానికి దయచేసి ఈ ప్రశ్నకు సమాధానం ఇవ్వండి.", "invalid_value": "దయచేసి సరైన విలువ నమోదు చేయండి.", "value_required": "ఈ ఫీల్డ్ అవసరం.", "checking_crop_health": "మీ పంట ఆరోగ్యాన్ని పరిశీలిస్తోంది...", "watering_recommendation": "నీటి సలహా:", "recommended_amount": "సిఫారసు చేసిన మొత్తం:", "best_time": "ఉత్తమ సమయం:", "reason": "కారణం:", "next_action": "తదుపరి చర్య:", "water_now": "ఇప్పుడు నీరు పెట్టండి", "wait": "వేచి ఉండండి", "irrigate_soon": "త్వరలో నీరు పెట్టండి", "do_not_irrigate": "నీరు పెట్టవద్దు", "estimated_harvest": "అంచనా దిగుబడి:", "expected_period": "ఆశించిన కోత కాలం:", "main_factors": "ప్రధాన కారకాలు:", "suggestion": "సూచన:", "direct_answer": "నేరుగా సమాధానం", "what_you_should_do": "మీరు ఏమి చేయాలి", "important_note": "ముఖ్యమైన గమనిక", "leaf_status": "ఆకు స్థితి", "possible_problem": "సాధ్యమైన సమస్య", "recommended_actions": "సిఫారసు చేసిన చర్యలు", "prevention": "నివారణ", "confidence_limitations": "విశ్వాసం మరియు పరిమితులు",
          "q_soil_moisture": "నేల తేమ స్థాయి ఎంత?", "q_soil_moisture_desc": "మీ నేలలో తేమ శాతం నమోదు చేయండి. నేల తేమ మీటర్ ఉపయోగించండి లేదా నేల ఎలా ఉందో బట్టి అంచనా వేయండి.", "q_soil_ph": "నేల pH స్థాయి ఎంత?", "q_soil_ph_desc": "pH మీ నేల ఎంత ఆమ్లం లేదా క్షారంగా ఉందో కొలుస్తుంది. 7 తటస్థం. చాలా పంటలు 6.0 నుండి 7.5 ఇష్టపడతాయి.", "q_nitrogen": "నత్రజని స్థాయి ఎంత?", "q_nitrogen_desc": "నత్రజని ఆకుల పెరుగుదలకు సహాయపడుతుంది. తక్కువ అంటే పసుపు ఆకులు, తగినంత అంటే ఆరోగ్యకరమైన ఆకుపచ్చ ఆకులు.", "q_phosphorus": "భాస్వరం స్థాయి ఎంత?", "q_phosphorus_desc": "భాస్వరం వేళ్లు మరియు విత్తనాలకు సహాయపడుతుంది. తక్కువ అంటే బలహీనమైన వేళ్లు, తగినంత అంటే బలమైన వేళ్లు.", "q_potassium": "పొటాషియం స్థాయి ఎంత?", "q_potassium_desc": "పొటాషియం మొక్కల మొత్తం ఆరోగ్యానికి మరియు వ్యాధి నిరోధకశక్తికి సహాయపడుతుంది. తక్కువ అంటే బలహీనమైన మొక్కలు.", "q_ec": "విద్యుత్ వాహకత (EC) ఎంత?", "q_ec_desc": "EC నేలలో ఉప్పును కొలుస్తుంది. ఎక్కువ ఉప్పు మొక్కలకు హానికరం. తక్కువ నుండి మధ్యస్థం సాధారణంగా మంచిది.", "q_issues": "పంటకు ఏవైనా సమస్యలు ఉన్నాయా?", "q_issues_desc": "పసుపు ఆకులు, మచ్చలు, వాడిపోవడం లేదా పురుగులు వంటి ఏవైనా సమస్యలను వివరించండి.", "q_growth_stage": "పంట ఎదుగుదల దశ ఏమిటి?", "q_growth_stage_desc": "మీ పంట ప్రస్తుత దశను ఎంచుకోండి. మొలక అంటే చిన్న మొక్కలు. వృద్ధి దశ అంటే ఆకుల పెరుగుదల. పూత దశ అంటే పూలు రావడం. కాయల దశ అంటే కాయలు రావడం. పక్వ దశ అంటే కోతకు దగ్గరగా ఉండటం.",
          "q_crop_type": "మీరు ఏ పంట పండిస్తున్నారు?", "q_crop_type_desc": "జాబితా నుండి పంట రకాన్ని ఎంచుకోండి.", "q_planting_date": "మీరు ఎప్పుడు పంట నాటారు?", "q_planting_date_desc": "మీరు విత్తనాలు నాటిన తేదీని నమోదు చేయండి.", "q_plant_height": "సగటు మొక్క ఎత్తు ఎంత?", "q_plant_height_desc": "నేల నుండి పైకి మొక్క ఎత్తును సెంటీమీటర్లలో కొలవండి.", "q_branches": "ప్రతి మొక్కకు ఎన్ని కొమ్మలు?", "q_branches_desc": "సగటు మొక్కపై ప్రధాన కొమ్మల సంఖ్యను లెక్కించండి.", "q_fruit_count": "ప్రతి మొక్కకు ఎన్ని కాయలు లేదా బోళ్లు?", "q_fruit_count_desc": "సగటు మొక్కపై కాయలు, పప్పులు లేదా పత్తి బోళ్ల సంఖ్యను లెక్కించండి.", "q_fruit_size": "సగటు కాయ పరిమాణం ఎంత?", "q_fruit_size_desc": "సగటు కాయ పరిమాణాన్ని సెంటీమీటర్లలో కొలవండి.", "q_temperature": "ప్రస్తుత ఉష్ణోగ్రత ఎంత?", "q_temperature_desc": "ప్రస్తుత గాలి ఉష్ణోగ్రతను డిగ్రీల సెల్సియస్‌లో నమోదు చేయండి.", "q_humidity": "గాలిలో తేమ స్థాయి ఎంత?", "q_humidity_desc": "ప్రస్తుత తేమ శాతాన్ని నమోదు చేయండి.", "q_rainfall": "ఇటీవల వర్షపాతం ఎంత?", "q_rainfall_desc": "గత కొన్ని రోజుల్లో మొత్తం వర్షపాతాన్ని మిల్లీమీటర్లలో నమోదు చేయండి.", "q_npk": "ఎరువు/NPK స్థాయి ఎంత?", "q_npk_desc": "తక్కువ అంటే మీరు చాలా ఎరువు వేయలేదు. తగినంత అంటే మీరు సరిపడా ఎరువు వేశారు.", "q_pest_severity": "పురుగు లేదా వ్యాధి నష్టం ఎంత తీవ్రం?", "q_pest_severity_desc": "పురుగులు లేదా వ్యాధుల ద్వారా దెబ్బతిన్న మొక్కల శాతాన్ని అంచనా వేయండి. 0 అంటే నష్టం లేదు, 100 అంటే తీవ్రమైన నష్టం.",
          "seedling": "మొలక", "vegetative": "వృద్ధి దశ", "flowering": "పూత దశ", "fruiting": "కాయల దశ", "maturity": "పక్వ దశ"},
    "hi": {"hello": "आज मैं आपकी कैसे मदद कर सकता हूँ?", "leaf": "मेरी पत्ती जाँचें", "health": "फसल का स्वास्थ्य जाँचें", "water": "सिंचाई सलाह", "harvest": "कटाई का अनुमान", "ask": "फार्ममित्र से पूछें", "recommend": "फसल अनुशंसा", "today": "आज का मौसम", "need": "आपको क्या चाहिए?", "listen": "सुन रहा हूँ...", "speak": "बोलने के लिए टैप करें", "stop": "सुनना बंद करें", "analyzing": "विश्लेषण हो रहा है...", "what": "क्या", "when": "कब", "why": "क्यों", "feedback": "क्या यह मददगार था?", "yes": "हाँ", "no": "नहीं", "reanalyze": "पुनः विश्लेषण करें",
          "step": "चरण", "of": "में से", "next": "अगला", "back": "पीछे", "submit": "जमा करें", "cancel": "रद्द करें", "retry": "पुनः प्रयास करें", "loading": "लोड हो रहा है...", "checking": "आपकी फसल का स्वास्थ्य जांच रहा है...", "getting_advice": "सिंचाई सलाह मिल रही है...", "estimating": "फसल कटाई का अनुमान लगा रहा है...", "please_answer": "जारी रखने के लिए कृपया इस सवाल का जवाब दें.", "invalid_value": "कृपया एक मान्य मान दर्ज करें.", "value_required": "यह फ़ील्ड आवश्यक है.", "checking_crop_health": "आपकी फसल का स्वास्थ्य जांच रहा है...", "watering_recommendation": "सिंचाई सलाह:", "recommended_amount": "अनुशंसित मात्रा:", "best_time": "सर्वोत्तम समय:", "reason": "कारण:", "next_action": "अगली कार्रवाई:", "water_now": "अभी पानी दें", "wait": "रुकें", "irrigate_soon": "जल्द ही पानी दें", "do_not_irrigate": "पानी न दें", "estimated_harvest": "अनुमानित फसल:", "expected_period": "अपेक्षित कटाई अवधि:", "main_factors": "मुख्य कारक:", "suggestion": "सुझाव:", "direct_answer": "सीधा उत्तर", "what_you_should_do": "आपको क्या करना चाहिए", "important_note": "महत्वपूर्ण नोट", "leaf_status": "पत्ती की स्थिति", "possible_problem": "संभावित समस्या", "recommended_actions": "अनुशंसित कार्य", "prevention": "रोकथाम", "confidence_limitations": "विश्वास और सीमाएं",
          "q_soil_moisture": "मिट्टी में नमी का स्तर क्या है?", "q_soil_moisture_desc": "अपनी मिट्टी में नमी प्रतिशत दर्ज करें. मिट्टी की नमी मीटर का उपयोग करें या मिट्टी कैसी महसूस होती है इसके आधार पर अनुमान लगाएं.", "q_soil_ph": "मिट्टी का pH स्तर क्या है?", "q_soil_ph_desc": "pH मापता है कि आपकी मिट्टी कितनी अम्लीय या क्षारीय है. 7 तटस्थ है. अधिकांश फसलों को 6.0 से 7.5 पसंद है.", "q_nitrogen": "नाइट्रोजन का स्तर क्या है?", "q_nitrogen_desc": "नाइट्रोजन पत्तियों के विकास में मदद करता है. कम का मतलब पीले पत्ते, पर्याप्त का मतलब हरे स्वस्थ पत्ते.", "q_phosphorus": "फास्फोरस का स्तर क्या है?", "q_phosphorus_desc": "फास्फोरस जड़ों और बीजों में मदद करता है. कम का मतलब कमजोर जड़ें, पर्याप्त का मतलब मजबूत जड़ें.", "q_potassium": "पोटैशियम का स्तर क्या है?", "q_potassium_desc": "पोटैशियम समग्र पौधे स्वास्थ्य और रोग प्रतिरोधक क्षमता में मदद करता है. कम का मतलब कमजोर पौधे.", "q_ec": "विद्युत चालकता (EC) क्या है?", "q_ec_desc": "EC मिट्टी में नमक मापता है. अधिक नमक पौधों को नुकसान पहुंचा सकता है. कम से मध्यम आमतौर पर अच्छा है.", "q_issues": "फसल में कोई समस्या है?", "q_issues_desc": "पीले पत्ते, धब्बे, मुरझाना या कीट जैसी किसी भी समस्या का वर्णन करें.", "q_growth_stage": "फसल की वृद्धि अवस्था क्या है?", "q_growth_stage_desc": "अपनी फसल की वर्तमान अवस्था चुनें. पौधा छोटे पौधे हैं. पात्रीय वृद्धि पत्ती विकास है. पुष्पन जब फूल दिखाई देते हैं. फलन जब फल बनते हैं. परिपक्वता कटाई के समय के पास है.",
          "q_crop_type": "आप कौन सी फसल उगा रहे हैं?", "q_crop_type_desc": "सूची से फसल का प्रकार चुनें.", "q_planting_date": "आपने फसल कब लगाई?", "q_planting_date_desc": "जब आपने बीज बोए थे उस तारीख दर्ज करें.", "q_plant_height": "औसत पौधे की ऊंचाई क्या है?", "q_plant_height_desc": "जमीन से ऊपर तक पौधे की ऊंचाई सेंटीमीटर में मापें.", "q_branches": "प्रति पौधे कितनी शाखाएं?", "q_branches_desc": "एक औसत पौधे पर मुख्य शाखाओं की संख्या गिनें.", "q_fruit_count": "प्रति पौधे कितने फल या कपास?", "q_fruit_count_desc": "एक औसत पौधे पर फल, फली या कपास की संख्या गिनें.", "q_fruit_size": "औसत फल का आकार क्या है?", "q_fruit_size_desc": "औसत फल के आकार को सेंटीमीटर में मापें.", "q_temperature": "वर्तमान तापमान क्या है?", "q_temperature_desc": "वर्तमान हवा का तापामान डिग्री सेंटीग्रेड में दर्ज करें.", "q_humidity": "नमी का स्तर क्या है?", "q_humidity_desc": "वर्तमान नमी प्रतिशत दर्ज करें.", "q_rainfall": "हाल ही में बारिश कितनी हुई?", "q_rainfall_desc": "पिछले कुछ दिनों में कुल बारिश मिलीमीटर में दर्ज करें.", "q_npk": "खाद/NPK स्तर क्या है?", "q_npk_desc": "कम का मतलब आपने बहुत खाद नहीं डाला. पर्याप्त का मतलब आपने पर्याप्त खाद डाला.", "q_pest_severity": "कीट या रोग क्षति कितनी गंभीर है?", "q_pest_severity_desc": "कीटों या रोगों से प्रभावित पौधों का प्रतिशत अनुमान लगाएं. 0 का मतलब कोई नुकसान नहीं, 100 का मतलब गंभीर नुकसान.",
          "seedling": "पौधा", "vegetative": "पात्रीय वृद्धि", "flowering": "पुष्पन", "fruiting": "फलन", "maturity": "परिपक्वता"},
    "ta": {"hello": "இன்று நான் உங்களுக்கு எப்படி உதவலாம்?", "leaf": "இலையைச் சரிபார்க்கவும்", "health": "பயிர் ஆரோக்கியம்", "water": "நீர் பாய்ச்சும் ஆலோசனை", "harvest": "அறுவடை மதிப்பீடு", "ask": "FarmMitra-விடம் கேளுங்கள்", "recommend": "பயிர் பரிந்துரை", "today": "இன்றைய வானிலை", "need": "உங்களுக்கு என்ன வேண்டும்?", "listen": "கேட்குகிறது...", "speak": "பேச தட்டவும்", "stop": "கேட்பதை நிறுத்தவும்", "analyzing": "பகுப்பாய்வு செய்கிறது...", "what": "என்ன", "when": "எப்போது", "why": "ஏன்", "feedback": "இது பயனுள்ளதா?", "yes": "ஆம்", "no": "இல்லை", "reanalyze": "மீண்டும் பகுப்பாய்வு செய்",
          "step": "படி", "of": "இல்", "next": "அடுத்தது", "back": "பின்", "submit": "சமர்ப்பிக்கவும்", "cancel": "ரத்து செய்", "retry": "மீண்டும் முயற்சிக்கவும்", "loading": "ஏற்றுகிறது...", "checking": "உங்கள் பயிர் ஆரோக்கியத்தை சரிபார்க்கிறது...", "getting_advice": "நீர் பாசன ஆலோசனை பெறுகிறது...", "estimating": "அறுவடை மதிப்பீடு செய்கிறது...", "please_answer": "தொடர இந்த கேள்விக்கு பதிலளிக்கவும்.", "invalid_value": "தயவு செய்து சரியான மதிப்பை உள்ளிடவும்.", "value_required": "இந்த புலம் தேவை.", "checking_crop_health": "உங்கள் பயிர் ஆரோக்கியத்தை சரிபார்க்கிறது...", "watering_recommendation": "நீர் பாசன பரிந்துரை:", "recommended_amount": "பரிந்துரைக்கப்பட்ட அளவு:", "best_time": "சிறந்த நேரம்:", "reason": "காரணம்:", "next_action": "அடுத்த நடவடிக்கை:", "water_now": "இப்போது தண்ணீ போ", "wait": "காத்திருங்கள்", "irrigate_soon": "விரைவில் தண்ணீ போ", "do_not_irrigate": "தண்ணீ போ வேண்டாம்", "estimated_harvest": "மதிப்பிடப்பட்ட அறுவடை:", "expected_period": "எதிர்பார்க்களப்பட்ட அறுவடை காலம்:", "main_factors": "முக்கிய காரணிகள்:", "suggestion": "பரிந்துரை:", "direct_answer": "நேரடி பதில்", "what_you_should_do": "நீங்கள் என்ன செய்ய வேண்டும்", "important_note": "முக்கிய குறிப்பு", "leaf_status": "இலை நிலை", "possible_problem": "சாத்தியமான பிரச்சனை", "recommended_actions": "பரிந்துரைக்கப்பட்ட செயல்கள்", "prevention": "தடுப்பு", "confidence_limitations": "நம்பிக்கை மற்றும் வரம்புகள்",
          "q_soil_moisture": "மண் ஈரப்பதம் அளவு என்ன?", "q_soil_moisture_desc": "உங்கள் மண்ணில் ஈரப்பத சதவீதத்தை உள்ளிடவும். மண் ஈரப்பத மீட்டரைப் பயன்படுத்தவும் அல்லது மண் எப்படி உள்ளது என்பதன் அடிப்படையில் மதிப்பிடவும்.", "q_soil_ph": "மண் pH அளவு என்ன?", "q_soil_ph_desc": "pH உங்கள் மண் எவ்வளவு அமிலமானது அல்லது காரமானது என்பதை அளவிடுகிறது. 7 நடுநிலையானது. பெரும்பாலான பயிர்கள் 6.0 முதல் 7.5 வரை விரும்புகின்றன.", "q_nitrogen": "நைட்ரஜன் அளவு என்ன?", "q_nitrogen_desc": "நைட்ரஜன் இலைகள் வளர்வதற்கு உதவுகிறது. குறைந்த என்றால் மஞ்சள் இலைகள், போதுமான என்றால் பச்சை ஆரோக்கியமான இலைகள்.", "q_phosphorus": "பாஸ்பரஸ் அளவு என்ன?", "q_phosphorus_desc": "பாஸ்பரஸ் வேர்கள் மற்றும் விதைகளுக்கு உதவுகிறது. குறைந்த என்றால் பலவீனமான வேர்கள், போதுமான என்றால் வலுவான வேர்கள்.", "q_potassium": "பொட்டாசியம் அளவு என்ன?", "q_potassium_desc": "பொட்டாசியம் ஒட்டுமொத்த தாவர ஆரோக்கியம் மற்றும் நோய் எதிர்ப்பு சக்திக்கு உதவுகிறது. குறைந்த என்றால் பலவீனமான தாவரங்கள்.", "q_ec": "மின்சாரம் கடத்துதிறன் (EC) என்ன?", "q_ec_desc": "EC மண்ணில் உள்ள உப்பை அளவிடுகிறது. அதிக உப்பு தாவரங்களுக்கு தீங்கு விளைவிக்கலாம். குறைந்த முதல் மிதமான வரை பொதுவாக நல்லது.", "q_issues": "பயிரில் எந்த பிரச்சனையும் உள்ளதா?", "q_issues_desc": "மஞ்சள் இலைகள், புள்ளிகள், வாடுதல் அல்லது பூச்சிகள் போன்ற எந்தவொரு பிரச்சனையையும் விவரிக்கவும்.", "q_growth_stage": "பயிர் வளர்ச்சி நிலை என்ன?", "q_growth_stage_desc": "உங்கள் பயிரின் தற்போதைய நிலையைத் தேர்வு செய்யவும். விதைத்தாள் சிறிய தாவரங்கள். இலையுருவாக்கம் இலை வளர்ச்சி. பூக்கும் பூக்கள் தோன்றும்போது. பழுத்த பழங்கள் உருவாகும்போது. முதிர்ச்சி அறுவடை நேரத்திற்கு அருகில்.",
          "q_crop_type": "நீங்கள் எந்தப் பயிரை வளர்க்கிறீர்கள்?", "q_crop_type_desc": "பட்டியலிலிருந்து பயிர் வகையைத் தேர்வு செய்யவும்.", "q_planting_date": "நீங்கள் பயிரை எப்போது நட்டீர்கள்?", "q_planting_date_desc": "நீங்கள் விதைகளை நட்ட தேதியை உள்ளிடவும்.", "q_plant_height": "சராசரி தாவர உயரம் என்ன?", "q_plant_height_desc": "தரையிலிருந்து மேல் வரை தாவரத்தின் உயரத்தை சென்டிமீட்டரில் அளவிடவும்.", "q_branches": "ஒரு தாவரத்திற்கு எத்தனை கிளைகள்?", "q_branches_desc": "ஒரு சராசரி தாவரத்தில் முக்கிய கிளைகளின் எண்ணிக்கையை எண்கவும்.", "q_fruit_count": "ஒரு தாவரத்திற்கு எத்தனை பழங்கள் அல்லது காய்கள்?", "q_fruit_count_desc": "ஒரு சராசரி தாவரத்தில் பழங்கள், பயறுகள் அல்லது பருத்தி காய்களின் எண்ணிக்கையை எண்கவும்.", "q_fruit_size": "சராசரி பழ அளவு என்ன?", "q_fruit_size_desc": "சராசரி பழத்தின் அளவை சென்டிமீட்டரில் அளவிடவும்.", "q_temperature": "தற்போதைய வெப்பநிலை என்ன?", "q_temperature_desc": "தற்போதைய காற்று வெப்பநிலையை டிகிரி செல்சியஸில் உள்ளிடவும்.", "q_humidity": "ஈரப்பத அளவு என்ன?", "q_humidity_desc": "தற்போதைய ஈரப்பத சதவீதத்தை உள்ளிடவும்.", "q_rainfall": "சமீபத்திய மழை எவ்வளவு?", "q_rainfall_desc": "கடந்த சில நாட்களில் மொத்த மழையை மில்லிமீட்டரில் உள்ளிடவும்.", "q_npk": "உரம்/NPK அளவு என்ன?", "q_npk_desc": "குறைந்த என்றால் நீங்கள் அதிக உரம் இடவில்லை. போதுமான என்றால் நீங்கள் போதுமான உரம் இட்டீர்கள்.", "q_pest_severity": "பூச்சி அல்லது நோற்றி சேதம் எவ்வளவு தீவிரமானது?", "q_pest_severity_desc": "பூச்சிகள் அல்லது நோய்களால் பாதிக்கப்பட்ட தாவரங்களின் சதவீதத்தை மதிப்பிடவும். 0 என்றால் சேதம் இல்லை, 100 என்றால் தீவிரமான சேதம்.",
          "seedling": "விதைத்தாள்", "vegetative": "இலையுருவாக்கம்", "flowering": "பூக்கும்", "fruiting": "பழுத்த", "maturity": "முதிர்ச்சி"},
    "kn": {"hello": "ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?", "leaf": "ನನ್ನ ಎಲೆಯನ್ನು ಪರಿಶೀಲಿಸಿ", "health": "ಬೆಳೆ ಆರೋಗ್ಯ ಪರಿಶೀಲಿಸಿ", "water": "ನೀರಾವರಿ ಸಲಹೆ", "harvest": "ಕೊಯ್ಲು ಅಂದಾಜು", "ask": "FarmMitra ಅನ್ನು ಕೇಳಿ", "recommend": "ಬೆಳೆ ಶಿಫಾರಸು", "today": "ಇಂದಿನ ಹವಾಮಾನ", "need": "ನಿಮಗೆ ಏನು ಬೇಕು?", "listen": "ಕೇಳುತ್ತಿದೆ...", "speak": "ಮಾತನಾಡಲು ಟ್ಯಾಪ್ ಮಾಡಿ", "stop": "ಕೇಳುವುದನ್ನು ನಿಲ್ಲಿಸಿ", "analyzing": "ವಿಶ್ಲೇಷಿಸುತ್ತಿದೆ...", "what": "ಏನು", "when": "ಯಾವಾಗ", "why": "ಏಕೆ", "feedback": "ಇದು ಸಹಾಯಕವಾಗಿತ್ತೇ?", "yes": "ಹೌದು", "no": "ಇಲ್ಲ", "reanalyze": "ಮತ್ತೆ ವಿಶ್ಲೇಷಿಸಿ",
          "step": "ಹಂತ", "of": "ರಲ್ಲ", "next": "ಮುಂದಿನ", "back": "ಹಿಂದಿನ", "submit": "ಸಲ್ಲಿಸಿ", "cancel": "ರದ್ದುಮಾಡಿ", "retry": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ", "loading": "ಲೋಡ್ ಆಗುತ್ತಿದೆ...", "checking": "ನಿಮ್ಮ ಬೆಳೆಯ ಆರೋಗ್ಯವನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದೆ...", "getting_advice": "ನೀರಾವರಿ ಸಲಹೆ ಪಡೆಯುತ್ತಿದೆ...", "estimating": "ಕೊಯ್ಲು ಅಂದಾಜು ಮಾಡುತ್ತಿದೆ...", "please_answer": "ಮುಂದುವರಿಸಲು ದಯವಿಟ್ಟು ಈ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಿ.", "invalid_value": "ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಮೌಲ್ಯವನ್ನು ನಮೂದಿಸಿ.", "value_required": "ಈ ಕ್ಷೇತ್ರ ಅಗತ್ಯವಿದೆ.", "checking_crop_health": "ನಿಮ್ಮ ಬೆಳೆಯ ಆರೋಗ್ಯವನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದೆ...", "watering_recommendation": "ನೀರಾವರಿ ಸಲಹೆ:", "recommended_amount": "ಶಿಫಾರಸು ಮಾಡಿದ ಪ್ರಮಾಣ:", "best_time": "ಉತ್ತಮ ಸಮಯ:", "reason": "ಕಾರಣ:", "next_action": "ಮುಂದಿನ ಕ್ರಮ:", "water_now": "ಈಗ ನೀರು ಹಾಕಿ", "wait": "ನಿರೀಕ್ಷಿಸಿ", "irrigate_soon": "ಶೀಘ್ರದಲ್ಲಿ ನೀರು ಹಾಕಿ", "do_not_irrigate": "ನೀರು ಹಾಕಬೇಡಿ", "estimated_harvest": "ಅಂದಾಜು ಕೊಯ್ಲು:", "expected_period": "ನಿರೀಕ್ಷಿತ ಕೊಯ್ಲು ಅವಧಿ:", "main_factors": "ಪ್ರಮುಖ ಅಂಶಗಳು:", "suggestion": "ಸಲಹೆ:", "direct_answer": "ನೇರ ಉತ್ತರ", "what_you_should_do": "ನೀವು ಏನು ಮಾಡಬೇಕು", "important_note": "ಮುಖ್ಯ ಟಿಪ್ಪಣಿ", "leaf_status": "ಎಲೆಯ ಸ್ಥಿತಿ", "possible_problem": "ಸಾಧ್ಯವಾದ ಸಮಸ್ಯೆ", "recommended_actions": "ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮಗಳು", "prevention": "ತಡೆಗಟ್ಟುವಿಕೆ", "confidence_limitations": "ವಿಶ್ವಾಸ ಮತ್ತು ಮಿತಿಗಳು",
          "q_soil_moisture": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಮಟ್ಟ ಎಷ್ಟು?", "q_soil_moisture_desc": "ನಿಮ್ಮ ಮಣ್ಣಿನಲ್ಲಿ ತೇವಾಂಶ ಶೇಕಡಾವಾರು ದಾಖಲಿಸಿ. ಮಣ್ಣಿನ ತೇವಾಂಶ ಮೀಟರ್ ಬಳಸಿ ಅಥವಾ ಮಣ್ಣು ಹೇಗಿದೆ ಎಂಬುದರ ಆಧಾರದ ಮೇಲೆ ಅಂದಾಜು ಮಾಡಿ.", "q_soil_ph": "ಮಣ್ಣಿನ pH ಮಟ್ಟ ಎಷ್ಟು?", "q_soil_ph_desc": "pH ನಿಮ್ಮ ಮಣ್ಣು ಎಷ್ಟು ಆಮ್ಲೀಯ ಅಥವಾ ಕ್ಷಾರೀಯವಾಗಿದೆ ಎಂದು ಅಳೆಯುತ್ತದೆ. 7 ತಟಸ್ಥವಾಗಿದೆ. ಹೆಚ್ಚಿನ ಬೆಳೆಗಳು 6.0 ರಿಂದ 7.5 ಅನ್ನು ಇಷ್ಟಪಡುತ್ತವೆ.", "q_nitrogen": "ನೈಟ್ರೋಜೆನ್ ಮಟ್ಟ ಎಷ್ಟು?", "q_nitrogen_desc": "ನೈಟ್ರೋಜೆನ್ ಎಲೆಗಳ ಬೆಳವಣಿಗೆಗೆ ಸಹಾಯ ಮಾಡುತ್ತದೆ. ಕಡಿಮೆ ಎಂದರೆ ಹಳದಿ ಎಲೆಗಳು, ಸಾಕಷ್ಟು ಎಂದರೆ ಆರೋಗ್ಯಕರ ಹಸಿರು ಎಲೆಗಳು.", "q_phosphorus": "ಫಾಸ್ಫರಸ್ ಮಟ್ಟ ಎಷ್ಟು?", "q_phosphorus_desc": "ಫಾಸ್ಫರಸ್ ಬೇರುಗಳು ಮತ್ತು ಬೀಜಗಳಿಗೆ ಸಹಾಯ ಮಾಡುತ್ತದೆ. ಕಡಿಮೆ ಎಂದರೆ ದುರ್ಬಲ ಬೇರುಗಳು, ಸಾಕಷ್ಟು ಎಂದರೆ ಬಲಿಷ್ಠ ಬೇರುಗಳು.", "q_potassium": "ಪೊಟ್ಯಾಸಿಯಮ್ ಮಟ್ಟ ಎಷ್ಟು?", "q_potassium_desc": "ಪೊಟ್ಯಾಸಿಯಮ್ ಒಟ್ಟಾರೆ ಸಸ್ಯ ಆರೋಗ್ಯ ಮತ್ತು ರೋಗ ನಿರೋಧಕ ಶಕ್ತಿಗೆ ಸಹಾಯ ಮಾಡುತ್ತದೆ. ಕಡಿಮೆ ಎಂದರೆ ದುರ್ಬಲ ಸಸ್ಯಗಳು.", "q_ec": "ವಿದ್ಯುತ್ ವಾಹಕತೆ (EC) ಎಷ್ಟು?", "q_ec_desc": "EC ಮಣ್ಣಿನಲ್ಲಿನ ಲವಣವನ್ನು ಅಳೆಯುತ್ತದೆ. ಹುಚ್ಚಿನ ಲವಣ ಸಸ್ಯಗಳಿಗೆ ಹಾನಿಕಾರಕವಾಗಬಹುದು. ಕಡಿಮೆ ಇಂದ ಮಧ್ಯಮ ಸಾಮಾನ್ಯವಾಗಿ ಒಳ್ಳೆಯದು.", "q_issues": "ಬೆಳೆಯಲ್ಲಿ ಯಾವುದೇ ಸಮಸ್ಯೆಯಿದೆಯೇ?", "q_issues_desc": "ಹಳದಿ ಎಲೆಗಳು, ಚುಕ್ಕೆಗಳು, ಒಣಗುವಿಕೆ ಅಥವಾ ಕೀಟಗಳಂತಹ ಯಾವುದೇ ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ.", "q_growth_stage": "ಬೆಳೆಯ ಬೆಳವಣಿಗೆಯ ಹಂತ ಯಾವುದು?", "q_growth_stage_desc": "ನಿಮ್ಮ ಬೆಳೆಯ ಪ್ರಸ್ತುತ ಹಂತವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ. ಸಸಿ ಸಣ್ಣ ಸಸ್ಯಗಳು. ಕಾಂಡಬೆಳವಣಿಗೆ ಎಲೆಗಳ ಬೆಳವಣಿಗೆ. ಹೂವಿಡುವಿಕೆ ಹೂವುಗಳು ಕಾಣಿಸಿದಾಗ. ಹಣ್ಣುಗಳು ಹಣ್ಣುಗಳು ರಚನೆಯಾದಾಗ. ಪಕ್ವತೆ ಕೊಯ್ಲು ಸಮಯದ ಹತ್ತಿರ.",
          "q_crop_type": "ನೀವು ಯಾವ ಬೆಳೆಯನ್ನು ಬೆಳೆಸುತ್ತಿದ್ದೀರಿ?", "q_crop_type_desc": "ಪಟ್ಟಿಯಿಂದ ಬೆಳೆಯ ಪ್ರਕಾರವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.", "q_planting_date": "ನೀವು ಬೆಳೆಯನ್ನು ಯಾವಾಗ ನೆಟ್ಟಿದ್ದೀರಿ?", "q_planting_date_desc": "ನೀವು ಬೀಜಗಳನ್ನು ನೆಟ್ಟ ದಿನಾಂಕವನ್ನು ದಾಖಲಿಸಿ.", "q_plant_height": "ಸರಾಸರಿ ಸಸ್ಯ ಎತ್ತರ ಎಷ್ಟು?", "q_plant_height_desc": "ನೆಲದಿಂದ ಮೇಲಕ್ಕೆ ಸಸ್ಯದ ಎತ್ತರವನ್ನು ಸೆಂಟಿಮೀಟರ್‌ನಲ್ಲಿ ಅಳೆಯಿರಿ.", "q_branches": "ಪ್ರತಿ ಸಸ್ಯಕ್ಕೆ ಎಷ್ಟು ಕೊಂಬೆಗಳು?", "q_branches_desc": "ಸರಾಸರಿ ಸಸ್ಯದಲ್ಲಿನ ಮುಖ್ಯ ಕೊಂಬೆಗಳ ಸಂಖ್ಯೆಯನ್ನು ಎಣಿಸಿ.", "q_fruit_count": "ಪ್ರತಿ ಸಸ್ಯಕ್ಕೆ ಎಷ್ಟು ಹಣ್ಣುಗಳು ಅಥವಾ ಹೂವುಗಳು?", "q_fruit_count_desc": "ಸರಾಸರಿ ಸಸ್ಯದಲ್ಲಿನ ಹಣ್ಣುಗಳು, ಹುಸಿಗಳು ಅಥವಾ ಹತ್ತಿ ಹೂವುಗಳ ಸಂಖ್ಯೆಯನ್ನು ಎಣಿಸಿ.", "q_fruit_size": "ಸರಾಸರಿ ಹಣ್ಣಿನ ಗಾತ್ರ ಎಷ್ಟು?", "q_fruit_size_desc": "ಸರಾಸರಿ ಹಣ್ಣಿನ ಗಾತ್ರವನ್ನು ಸೆಂಟಿಮೀಟರ್‌ನಲ್ಲಿ ಅಳೆಯಿರಿ.", "q_temperature": "ಪ್ರಸ್ತುತ ತಾಪಮಾನ ಎಷ್ಟು?", "q_temperature_desc": "ಪ್ರಸ್ತುತ ಗಾಳಿಯ ತಾಪಮಾನವನ್ನು ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್‌ನಲ್ಲಿ ದಾಖಲಿಸಿ.", "q_humidity": "ತೇವಾಂಶ ಮಟ್ಟ ಎಷ್ಟು?", "q_humidity_desc": "ಪ್ರಸ್ತುತ ತೇವಾಂಶ ಶೇಕಡಾವಾರು ದಾಖಲಿಸಿ.", "q_rainfall": "ಇತ್ತೀಚಿನ ಮಳೆ ಎಷ್ಟು?", "q_rainfall_desc": "ಕಳೆದ ಕೆಲವು ದಿನಗಳಲ್ಲಿ ಒಟ್ಟು ಮಳೆಯನ್ನು ಮಿಲಿಮೀಟರ್‌ನಲ್ಲಿ ದಾಖಲಿಸಿ.", "q_npk": "ಗೊಬ್ಬರು/NPK ಮಟ್ಟ ಎಷ್ಟು?", "q_npk_desc": "ಕಡಿಮೆ ಎಂದರೆ ನೀವು ಹೆಚ್ಚು ಗೊಬ್ಬರ ಹಾಕಿಲ್ಲ. ಸಾಕಷ್ಟು ಎಂದರೆ ನೀವು ಸಾಕಷ್ಟು ಗೊಬ್ಬರ ಹಾಕಿದ್ದೀರಿ.", "q_pest_severity": "ಕೀಟ ಅಥವಾ ರೋಗ ಹಾನಿ ಎಷ್ಟು ತೀವ್ರವಾಗಿದೆ?", "q_pest_severity_desc": "ಕೀಟಗಳು ಅಥವಾ ರೋಗಗಳಿಂದ ಪೀಡಿತವಾದ ಸಸ್ಯಗಳ ಶೇಕಡಾವಾರು ಅಂದಾಜು ಮಾಡಿ. 0 ಎಂದರೆ ಹಾನಿ ಇಲ್ಲ, 100 ಎಂದರೆ ತೀವ್ರ ಹಾನಿ.",
          "seedling": "ಸಸಿ", "vegetative": "ಕಾಂಡಬೆಳವಣಿಗೆ", "flowering": "ಹೂವಿಡುವಿಕೆ", "fruiting": "ಹಣ್ಣುಗಳು", "maturity": "ಪಕ್ವತೆ"},
    "mr": {"hello": "आज मी तुम्हाला कशी मदत करू?", "leaf": "पान तपासा", "health": "पीक आरोग्य तपासा", "water": "पाणी देण्याचा सल्ला", "harvest": "कापणीचा अंदाज", "ask": "फार्ममित्राला विचारा", "recommend": "पीक शिफारस", "today": "आजचे हवामान", "need": "तुम्हाला काय हवे आहे?", "listen": "ऐकत आहे...", "speak": "बोलण्यासाठी टॅप करा", "stop": "ऐकणे थांबवा", "analyzing": "विश्लेषण करत आहे...", "what": "काय", "when": "केव्हा", "why": "का", "feedback": "हे मदतीचे होते का?", "yes": "होय", "no": "नाही", "reanalyze": "पुन्हा विश्लेषण करा",
          "step": "पाऊल", "of": "पैकी", "next": "पुढील", "back": "मागे", "submit": "सादर करा", "cancel": "रद्द करा", "retry": "पुन्हा प्रयत्न करा", "loading": "लोड होत आहे...", "checking": "तुमच्या पिकाचे आरोग्य तपासत आहे...", "getting_advice": "सिंचन सल्ला मिळत आहे...", "estimating": "कापणीचा अंदाज लावत आहे...", "please_answer": "सुरू ठेवण्यासाठी कृपया या प्रश्नाचे उत्तर द्या.", "invalid_value": "कृपया वैध मूल्य प्रविष्ट करा.", "value_required": "हे फील्ड आवश्यक आहे.", "checking_crop_health": "तुमच्या पिकाचे आरोग्य तपासत आहे...", "watering_recommendation": "सिंचन सल्ला:", "recommended_amount": "शिफारस केलेली रक्कम:", "best_time": "उत्तम वेळ:", "reason": "कारण:", "next_action": "पुढीची कृती:", "water_now": "आता पाणी द्या", "wait": "थांबा", "irrigate_soon": "लवकर पाणी द्या", "do_not_irrigate": "पाणी देऊ नका", "estimated_harvest": "अंदाजित कापणी:", "expected_period": "अपेक्षित कापणी कालावधी:", "main_factors": "मुख्य घटक:", "suggestion": "सल्ला:", "direct_answer": "थेट उत्तर", "what_you_should_do": "तुम्ही काय करावे", "important_note": "महत्त्वाची टीप", "leaf_status": "पानाची स्थिती", "possible_problem": "संभाव्य समस्या", "recommended_actions": "शिफारस केलेली कृती", "prevention": "प्रतिबंध", "confidence_limitations": "विश्वास आणि मर्यादा",
          "q_soil_moisture": "मातीतील ओलावा पातळी किती?", "q_soil_moisture_desc": "तुमच्या मातीतील ओलावा टक्का नोंदवा. माती ओलावा मीटर वापरा किंवा माती कशी आहे हे तपासून अंदाज काढा.", "q_soil_ph": "मातीची pH पातळी किती?", "q_soil_ph_desc": "pH मोजतो की तुमची माती किती आम्लीय किंवा क्षारीय आहे. 7 तटस्थ आहे. बहुतेक पिकांना 6.0 ते 7.5 आवडते.", "q_nitrogen": "नायट्रोजनची पातळी किती?", "q_nitrogen_desc": "नायट्रोजन पाने वाढण्यास मदत करतो. कमी म्हणजे पिवळी पाने, पुरेसे म्हणजे हिरवी आरोग्यदायी पाने.", "q_phosphorus": "फॉस्फरसची पातळी किती?", "q_phosphorus_desc": "फॉस्फरस मुळे आणि बियांना मदत करतो. कमी म्हणजे कमकुवत मुळे, पुरेसे म्हणजे मजबूत मुळे.", "q_potassium": "पोटॅशियमची पातळी किती?", "q_potassium_desc": "पोटॅशियम एकंदरित वनस्पती आरोग्य आणि रोग प्रतिकारशक्तीस मदत करतो. कमी म्हणजे कमकुवत वनस्पती.", "q_ec": "विद्युत चालकता (EC) किती?", "q_ec_desc": "EC मातीतील मीठ मोजतो. जास्त मीठ वनस्पतींना नाश करू शकते. कमी ते मध्यम सहसा चांगले असते.", "q_issues": "पिकात काही समस्या आहे का?", "q_issues_desc": "पिवळी पाने, ठिपके, कोमळवणे किंवा किडी सारख्या कोणत्याही समस्येचे वर्णन करा.", "q_growth_stage": "पिकाची वाढीची टप्पी कोणती?", "q_growth_stage_desc": "तुमच्या पिकाची सद्यस्थिती निवडा. रोपण लहान वनस्पती आहेत. वनस्पतीय वाढ पाने वाढत आहेत. फुलवणे जेव्हा फुले दिसतात. फळवणे जेव्हा फळे तयार होतात. परिपक्वता कापणीच्या वेळेजवळ आहे.",
          "q_crop_type": "तुम्ही कोणते पीक घेत आहात?", "q_crop_type_desc": "यादीतून पिकाचा प्रकार निवडा.", "q_planting_date": "तुम्ही पीक केव्हा लावले?", "q_planting_date_desc": "तुम्ही बिया लावलेली तारीख नोंदवा.", "q_plant_height": "सरासरी वनस्पतीची उंची किती?", "q_plant_height_desc": "जमिनीपासून वर वनस्पतीची उंची सेंटीमीटरमध्ये मोजा.", "q_branches": "प्रत्येक वनस्पतीला किती फांदे?", "q_branches_desc": "सरासरी वनस्पतीवरील मुख्य फांद्यांची संख्या मोजा.", "q_fruit_count": "प्रत्येक वनस्पतीला किती फळे किंवा कापस?", "q_fruit_count_desc": "सरासरी वनस्पतीवरील फळे, शेंगदाणे किंवा कापसाच्या कळ्यांची संख्या मोजा.", "q_fruit_size": "सरासरी फळाचा आकार किती?", "q_fruit_size_desc": "सरासरी फळाचा आकार सेंटीमीटरमध्ये मोजा.", "q_temperature": "वर्तमान तापमान किती?", "q_temperature_desc": "वर्तमान हवेचे तापमान अंश सेल्सिअसमध्ये नोंदवा.", "q_humidity": "ओलावा पातळी किती?", "q_humidity_desc": "वर्तमान ओलावा टक्का नोंदवा.", "q_rainfall": "अलीकडील पाऊस किती?", "q_rainfall_desc": "गेल्या काही दिवसांत एकूण पाऊस मिलिमीटरमध्ये नोंदवा.", "q_npk": "खत/NPK पातळी किती?", "q_npk_desc": "कमी म्हणजे तुम्ही खूप खत दिले नाही. पुरेसे म्हणजे तुम्ही पुरेसे खत दिले आहे.", "q_pest_severity": "किडी किंवा रोग नुकसान किती गंभीर आहे?", "q_pest_severity_desc": "किडी किंवा रोगांनी प्रभावित झालेल्या वनस्पतींचा टक्का अंदाज काढा. 0 म्हणजे नुकसान नाही, 100 म्हणजे गंभीर नुकसान.",
          "seedling": "रोपण", "vegetative": "वनस्पतीय वाढ", "flowering": "फुलवणे", "fruiting": "फळवणे", "maturity": "परिपक्वता"},
    "bn": {"hello": "আজ আমি কীভাবে সাহায্য করতে পারি?", "leaf": "আমার পাতা পরীক্ষা করুন", "health": "ফসলের স্বাস্থ্য পরীক্ষা করুন", "water": "সেচ পরামর্শ", "harvest": "ফসল কাটার অনুমান", "ask": "FarmMitra কে জিজ্ঞাসা করুন", "recommend": "ফসল সুপারিশ", "today": "আজকের আবহাওয়া", "need": "আপনার কী দরকার?", "listen": "শুনছি...", "speak": "কথা বলতে ট্যাপ করুন", "stop": "শোনা বন্ধ করুন", "analyzing": "বিশ্লেষণ করছে...", "what": "কি", "when": "কখন", "why": "কেন", "feedback": "এটি কি সহায়ক ছিল?", "yes": "হ্যাঁ", "no": "না", "reanalyze": "পুনরায় বিশ্লেষণ করুন",
          "step": "ধাপ", "of": "এর", "next": "পরবর্তী", "back": "পিছনে", "submit": "জমা দিন", "cancel": "বাতিল করুন", "retry": "পুনরায় চেষ্টা করুন", "loading": "লোড হচ্ছে...", "checking": "আপনার ফসলের স্বাস্থ্য পরীক্ষা করছে...", "getting_advice": "সেচ পরামর্শ পাচ্ছে...", "estimating": "ফসল কাটার অনুমান করছে...", "please_answer": "চালিয়ে যেতে দয়া করে এই প্রশ্নের উত্তর দিন.", "invalid_value": "দয়া করে একটি বৈধ মান লিখুন.", "value_required": "এই ক্ষেত্রটি প্রয়োজনীয়.", "checking_crop_health": "আপনার ফসলের স্বাস্থ্য পরীক্ষা করছে...", "watering_recommendation": "সেচ পরামর্শ:", "recommended_amount": "সুপারিশকৃত পরিমাণ:", "best_time": "সেরা সময়:", "reason": "কারণ:", "next_action": "পরবর্তী পদক্ষেপ:", "water_now": "এখন পানি দিন", "wait": "অপেক্ষা করুন", "irrigate_soon": "শীঘ্রই পানি দিন", "do_not_irrigate": "পানি দেবেন না", "estimated_harvest": "আনুমানিক ফসল:", "expected_period": "প্রত্যাশিত কাটাই সময়:", "main_factors": "প্রধান কারণসমূহ:", "suggestion": "পরামর্শ:", "direct_answer": "সরাসরি উত্তর", "what_you_should_do": "আপনার করণীয়", "important_note": "গুরুত্বপূর্ণ নোট", "leaf_status": "পাতার অবস্থা", "possible_problem": "সম্ভাব্য সমস্যা", "recommended_actions": "সুপারিশকৃত পদক্ষেপ", "prevention": "প্রতিরোধ", "confidence_limitations": "আস্থা এবং সীমাবদ্ধতা",
          "q_soil_moisture": "মাটীর আর্দ্রতা স্তর কত?", "q_soil_moisture_desc": "আপনার মাটীতে আর্দ্রতা শতাংশ লিখুন. মাটির আর্দ্রতা মিটার ব্যবহার করুন বা মাটি কেমন তা অনুমান করুন.", "q_soil_ph": "মাটির pH স্তর কত?", "q_soil_ph_desc": "pH পরিমাপ করে আপনার মাটি কতটা অম্লীয় বা ক্ষারীয়। 7 নিরপেক্ষ। বেশিরভাগ ফসল 6.0 থেকে 7.5 পছন্দ করে।", "q_nitrogen": "নাইট্রোজেন স্তর কত?", "q_nitrogen_desc": "নাইট্রোজেন পাতা বৃদ্ধিতে সাহায্য করে। কম মানে হলুদ পাতা, পর্যাপ্ত মানে সবুজ স্বাস্থ্যকর পাতা।", "q_phosphorus": "ফসফরাস স্তর কত?", "q_phosphorus_desc": "ফসফরাস শিকড় এবং বীজে সাহায্য করে। কম মানে দুর্বল শিকড়, পর্যাপ্ত মানে শক্তিশালী শিকড়।", "q_potassium": "পটাসিয়াম স্তর কত?", "q_potassium_desc": "পটাসিয়াম সামগ্রিক উদ্ভিদ স্বাস্থ্য এবং রোগ প্রতিরোধে সাহায্য করে। কম মানে দুর্বল উদ্ভিদ।", "q_ec": "বৈদ্যুতিক পরিবাহিতা (EC) কত?", "q_ec_desc": "EC মাটিতে লবণ পরিমাপ করে। বেশি লবণ উদ্ভিদের ক্ষতি করতে পারে। কম থেকে মাঝারি সাধারণত ভালো।", "q_issues": "ফসলে কোনো সমস্যা আছে?", "q_issues_desc": "হলুদ পাতা, দাগ, নিস্তেজ হওয়া বা পোকামাকড়ের মতো যেকোনো সমস্যা বর্ণনা করুন।", "q_growth_stage": "ফসলের বৃদ্ধি পর্যায় কী?", "q_growth_stage_desc": "আপনার ফসলের বর্তমান পর্যায় চয়ন করুন। চারা ছোট উদ্ভিদ। উদ্ভিদ বৃদ্ধি পাতা বৃদ্ধি। ফুলনা ফুল দেখা যায়। ফলন ফল তৈরি হয়। পরিপক্বতা কাটাই সময়ের কাছাকাছি।",
          "q_crop_type": "আপনি কোন ফসল চাষ করছেন?", "q_crop_type_desc": "তালিকা থেকে ফসলের ধরন নির্বাচন করুন।", "q_planting_date": "আপনি ফসল কবে লাগিয়েছিলেন?", "q_planting_date_desc": "আপনি বীজ লাগানোর তারিখ লিখুন।", "q_plant_height": "গড় উদ্ভিদের উচ্চতা কত?", "q_plant_height_desc": "মাটি থেকে উপরে উদ্ভিদের উচ্চতা সেন্টিমিটারে পরিমাপ করুন।", "q_branches": "প্রতি উদ্ভিদে কতগুলি শাখা?", "q_branches_desc": "একটি গড় উদ্ভিদে প্রধান শাখার সংখ্যা গণনা করুন।", "q_fruit_count": "প্রতি উদ্ভিদে কতগুলি ফল বা তুলা?", "q_fruit_count_desc": "একটি গড় উদ্ভিদে ফল, শিম বা তুলার সংখ্যা গণনা করুন।", "q_fruit_size": "গড় ফলের আকার কত?", "q_fruit_size_desc": "গড় ফলের আকার সেন্টিমিটারে পরিমাপ করুন।", "q_temperature": "বর্তমান তাপমাত্রা কত?", "q_temperature_desc": "বর্তমান বাতাসের তাপমাত্রা ডিগ্রি সেলসিয়াসে লিখুন।", "q_humidity": "আর্দ্রতা স্তর কত?", "q_humidity_desc": "বর্তমান আর্দ্রতা শতাংশ লিখুন।", "q_rainfall": "সাম্প্রতিক বৃষ্টিপাত কত?", "q_rainfall_desc": "গত কয়েক দিনে মোট বৃষ্টিপাত মিলিমিটারে লিখুন।", "q_npk": "সার/NPK স্তর কত?", "q_npk_desc": "কম মানে আপনি অনেক সার দেননি। পর্যাপ্ত মানে আপনি পর্যাপ্ত সার দিয়েছেন।", "q_pest_severity": "পোকামাকড় বা রোগ ক্ষতি কতটা গুরুতর?", "q_pest_severity_desc": "পোকামাকড় বা রোগগুলির দ্বারা ক্ষতিগ্রস্ত উদ্ভিদের শতাংশ অনুমান করুন। 0 মানে ক্ষতি নেই, 100 মানে গুরুতর ক্ষতি।",
          "seedling": "চারা", "vegetative": "উদ্ভিদ বৃদ্ধি", "flowering": "ফুলনা", "fruiting": "ফলন", "maturity": "পরিপক্বতা"},
    "gu": {"hello": "આજે હું તમારી કોઈ રીતે મદદ કરી શકું?", "leaf": "મારા પાનની તપાસ કરો", "health": "પાકના સ્વાસ્થ્યની તપાસ કરો", "water": "પાણી આપવાની સલાહ", "harvest": "પાક કાપણીનો અંદાજ", "ask": "FarmMitra ને પૂછો", "recommend": "પાક ભલામણ", "today": "આજનો હવામાન", "need": "તમને શું જરૂર છે?", "listen": "સાંભળી રહ્યું છે...", "speak": "બોલવા માટે ટેપ કરો", "stop": "સાંભળવું બંધ કરો", "analyzing": "વિશ્લેષણ કરી રહ્યું છે...", "what": "શું", "when": "ક્યારે", "why": "કેમ", "feedback": "શું આ મદદરૂપ હતું?", "yes": "હા", "no": "ના", "reanalyze": "ફરીથી વિશ્લેષણ કરો",
          "step": "પગલું", "of": "માંથી", "next": "આગળનું", "back": "પાછળ", "submit": "સબમિટ કરો", "cancel": "રદ કરો", "retry": "ફરીથી પ્રયત્ન કરો", "loading": "લોડ થઈ રહ્યું છે...", "checking": "તમારા પાકના સ્વાસ્થ્યની તપાસ કરી રહ્યું છે...", "getting_advice": "સિંચાઈ સલાહ મળી રહી છે...", "estimating": "પાક કાપણીનો અંદાજ લગાવી રહ્યું છે...", "please_answer": "ચાલુ રાખવા માટે કૃપા કરીને આ પ્રશ્નનો જવાબ આપો.", "invalid_value": "કૃપા કરીને માન્ય મૂલ્ય દાખલ કરો.", "value_required": "આ ફીલ્ડ જરૂરી છે.", "checking_crop_health": "તમારા પાકના સ્વાસ્થ્યની તપાસ કરી રહ્યું છે...", "watering_recommendation": "સિંચાઈ સલાહ:", "recommended_amount": "ભલામણ કરેલ રકમ:", "best_time": "શ્રેષ્ઠ સમય:", "reason": "કારણ:", "next_action": "આગળની ક્રિયા:", "water_now": "હવે પાણી આપો", "wait": "રાહ જુઓ", "irrigate_soon": "ટૂંકામાં પાણી આપો", "do_not_irrigate": "પાણી આપશો નહીં", "estimated_harvest": "અંદાજિત પાક:", "expected_period": "અપેક્ષિત કાપણી સમયગાળો:", "main_factors": "મુખ્ય પરિબળો:", "suggestion": "ભલામણ:", "direct_answer": "સીધો જવાબ", "what_you_should_do": "તમારે શું કરવું જોઈએ", "important_note": "મહત્વની નોંધ", "leaf_status": "પાનની સ્થિતિ", "possible_problem": "શક્ય સમસ્યા", "recommended_actions": "ભલામણ કરેલ ક્રિયાઓ", "prevention": "નિવારણ", "confidence_limitations": "વિશ્વાસ અને મર્યાદાઓ",
          "q_soil_moisture": "માટીની ભેજ સ્તર કેટલું?", "q_soil_moisture_desc": "તમારી માટીમાં ભેજ પ્રતિશત દાખલ કરો. માટી ભેજ મીટર વાપરો અથવા માટી કેવી છે તેના આધારે અંદાજ લગાવો.", "q_soil_ph": "માટીનું pH સ્તર કેટલું?", "q_soil_ph_desc": "pH માપે છે કે તમારી માટી કેટલી એસિડિક અથવા ક્ષારીય છે. 7 તટસ્થ છે. મોટાભાગા પાકો 6.0 થી 7.5 પસંદ કરે છે.", "q_nitrogen": "નાઇટ્રોજન સ્તર કેટલું?", "q_nitrogen_desc": "નાઇટ્રોજન પાંદડાના વિકાસમાં મદદ કરે છે. ઓછું એટલે પીળા પાંદડા, પર્યાપ્ત એટલે લીલા સ્વસ્થ પાંદડા.", "q_phosphorus": "ફોસ્ફરસ સ્તર કેટલું?", "q_phosphorus_desc": "ફોસ્ફરસ મૂળ અને બીજમાં મદદ કરે છે. ઓછું એટલે નબળા મૂળ, પર્યાપ્ત એટલે મજબૂત મૂળ.", "q_potassium": "પોટેશિયમ સ્તર કેટલું?", "q_potassium_desc": "પોટેશિયમ સમગ્ર છોડ સ્વાસ્થ્ય અને રોગ પ્રતિરોધક શક્તિમાં મદદ કરે છે. ઓછું એટલે નબળા છોડ.", "q_ec": "વિદ્યુત વાહકતા (EC) કેટલું?", "q_ec_desc": "EC માટીમાં મીઠું માપે છે. વધુ મીઠું છોડને નુકસાન પહોંચાડી શકે છે. ઓછું થી મધ્યમ સામાન્ય રીતે સારું છે.", "q_issues": "પાકમાં કોઈ સમસ્યા છે?", "q_issues_desc": "પીળા પાંદડા, ડાઘ, સૂકાઈ જતા હોય અથવા જીંતુઓ જેવી કોઈપણ સમસ્યાનું વર્ણન કરો.", "q_growth_stage": "પાકનો વિકાસ તબક્કો કયો?", "q_growth_stage_desc": "તમારા પાકનો વર્તમાન તબક્કો પસંદ કરો. વનસ્પતિ નાના છોડ છે. વનસ્પતિ વિકાસ પાંદડા વિકાસ. ફૂલવા જ્યારે ફૂલો દેખાય. ફળવા જ્યારે ફળો બને. પરિપક્વતા કાપણી સમયની નજીક.",
          "q_crop_type": "તમે કયો પાક ઉગાડો છો?", "q_crop_type_desc": "યાદીમાંથી પાકનો પ્રકાર પસંદ કરો.", "q_planting_date": "તમે પાક ક્યારે વાવ્યો?", "q_planting_date_desc": "તમે બીજ વાવેલી તારીખ દાખલ કરો.", "q_plant_height": "સરેરાશ છોડની ઊંચાઈ કેટલી?", "q_plant_height_desc": "જમીનથી ઉપર સુધી છોડની ઊંચાઈ સેન્ટીમીટરમાં માપો.", "q_branches": "દરેક છોડે કેટલી શાખાઓ?", "q_branches_desc": "સરેરાશ છોડ પર મુખ્ય શાખાઓની સંખ્યા ગણો.", "q_fruit_count": "દરેક છોડે કેટલા ફળો અથવા કાપાસ?", "q_fruit_count_desc": "સરેરાશ છોડ પર ફળો, ફળીઓ અથવા કપાસની સંખ્યા ગણો.", "q_fruit_size": "સરેરાશ ફળનું કદ કેટલું?", "q_fruit_size_desc": "સરેરાશ ફળનું કદ સેન્ટીમીટરમાં માપો.", "q_temperature": "વર્તમાન તાપમાન કેટલું?", "q_temperature_desc": "વર્તમાન હવાનું તાપમાન ડિગ્રી સેલ્સિયસમાં દાખલ કરો.", "q_humidity": "ભેજ સ્તર કેટલું?", "q_humidity_desc": "વર્તમાન ભેજ પ્રતિશત દાખલ કરો.", "q_rainfall": "તાજેતરનો વરસાદ કેટલો?", "q_rainfall_desc": "ગયેલા કેટલાક દિવસોમાં કુલ વરસાદ મિલીમીટરમાં દાખલ કરો.", "q_npk": "ખાતર/NPK સ્તર કેટલું?", "q_npk_desc": "ઓછું એટલે તમે ઘણું ખાતર નથી આપ્યું. પર્યાપ્ત એટલે તમે પર્યાપ્ત ખાતર આપ્યું છે.", "q_pest_severity": "જીંતુ અથવા રોગ નુકસાન કેટલું ગંભીર?", "q_pest_severity_desc": "જીંતુઓ અથવા રોગો દ્વારા પ્રભાવિત છોડનો ટકાવારી અંદાજ લગાવો. 0 એટલે નુકસાન નથી, 100 એટલે ગંભીર નુકસાન.",
          "seedling": "વનસ્પતિ", "vegetative": "વનસ્પતિ વિકાસ", "flowering": "ફૂલવા", "fruiting": "ફળવા", "maturity": "પરિપક્વતા"},
}


# Initialize Gemini (for image analysis only)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

# Crop maturity data (days to harvest)
CROP_MATURITY = {
    "rice": 120, "wheat": 110, "maize": 100, "cotton": 150, "sugarcane": 365,
    "tomato": 90, "potato": 100, "onion": 120, "chilli": 120, "brinjal": 100,
    "groundnut": 130, "soybean": 100, "mustard": 110, "sunflower": 100,
}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_farm():
    conn = db()
    farm = conn.execute("SELECT * FROM farm ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    # sqlite3.Row supports key indexing but not dict methods such as .get().
    # Return a regular mapping so callers can safely use either style.
    return dict(farm) if farm is not None else None


with db() as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS farm (
        id INTEGER PRIMARY KEY, crop TEXT NOT NULL, variety TEXT, sowing_date TEXT NOT NULL,
        location TEXT NOT NULL, farm_size TEXT, soil_type TEXT, irrigation TEXT,
        created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY, feature TEXT NOT NULL, image_path TEXT, 
        result TEXT NOT NULL, confidence REAL, language TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY, analysis_id INTEGER, helpful INTEGER NOT NULL,
        comment TEXT, created_at TEXT NOT NULL)""")


UI_RULES = {
    "te": {
        "Your simple farming assistant": "మీ సరళమైన వ్యవసాయ సహాయకుడు",
        "Practical support for your farm": "మీ వ్యవసాయానికి ఉపయోగకరమైన సహాయం",
        "Toggle voice": "వాయిస్‌ను ఆన్ లేదా ఆఫ్ చేయండి",
        "Microphone access not available": "మైక్రోఫోన్ అందుబాటులో లేదు",
        "Back to home": "ప్రధాన పేజీకి తిరిగి వెళ్లండి",
        "Choose a crop photo": "పంట ఫోటోను ఎంచుకోండి",
        "Take a photo or select one from your gallery (JPG, PNG, WebP · up to 8 MB)": "ఫోటో తీయండి లేదా గ్యాలరీ నుంచి ఎంచుకోండి (JPG, PNG, WebP · గరిష్ఠం 8 MB)",
        "Analyze": "విశ్లేషించండి", "Soil Moisture (%)": "నేల తేమ (%)", "Soil pH": "నేల pH",
        "Nitrogen (N)": "నత్రజని (N)", "Phosphorus (P)": "భాస్వరం (P)", "Potassium (K)": "పొటాషియం (K)",
        "Select level...": "స్థాయిని ఎంచుకోండి...", "Low": "తక్కువ", "Medium": "మధ్యస్థం", "Adequate": "తగినంత",
        "Electrical Conductivity (EC dS/m)": "విద్యుత్ వాహకత (EC dS/m)", "Any issues observed?": "ఏవైనా సమస్యలు కనిపించాయా?",
        "Describe any problems (yellowing, spots, wilting, etc.)": "పసుపు రంగు, మచ్చలు లేదా వాడిపోవడం వంటి సమస్యలను వివరించండి",
        "Check Crop Health": "పంట ఆరోగ్యాన్ని తనిఖీ చేయండి", "Watering advice": "నీటి పారుదల సలహా",
        "Enter soil moisture and crop growth stage. Temperature, humidity, and wind are added automatically from current weather data.": "నేల తేమ మరియు పంట ఎదుగుదల దశను నమోదు చేయండి. ఉష్ణోగ్రత, తేమ మరియు గాలి వేగం ప్రస్తుత వాతావరణం నుంచి స్వయంచాలకంగా వస్తాయి.",
        "e.g., 28": "ఉదా., 28", "Crop Growth Stage": "పంట ఎదుగుదల దశ", "Vegetative": "వృద్ధి దశ",
        "Flowering": "పూత దశ", "Fruit development": "కాయల అభివృద్ధి దశ", "Get Watering Advice": "నీటి సలహా పొందండి",
        "Priority": "ప్రాధాన్యత", "Water stress score": "నీటి ఒత్తిడి స్కోరు", "Reason": "కారణం",
        "Soil Moisture": "నేల తేమ", "Temperature": "ఉష్ణోగ్రత", "Humidity": "గాలిలో తేమ", "Wind": "గాలి వేగం",
        "Harvest estimate": "కోత అంచనా", "Enter your crop details and current field observations to see an estimate.": "అంచనా పొందడానికి పంట వివరాలు మరియు ప్రస్తుత పొలం పరిశీలనలను నమోదు చేయండి.",
        "Crop type": "పంట రకం", "Select crop...": "పంటను ఎంచుకోండి...", "Planting date": "నాటిన తేదీ",
        "Growth stage": "ఎదుగుదల దశ", "Fruiting": "కాయలు కాసే దశ", "Maturity": "పక్వ దశ",
        "Plant height (cm)": "మొక్క ఎత్తు (సెం.మీ.)", "Number of branches": "కొమ్మల సంఖ్య",
        "Number of fruits/bolls": "కాయలు/బోళ్ల సంఖ్య", "Average fruit/boll size (cm)": "సగటు కాయ/బోల్ పరిమాణం (సెం.మీ.)",
        "Soil moisture (%)": "నేల తేమ (%)", "Temperature (°C)": "ఉష్ణోగ్రత (°C)", "Humidity (%)": "గాలిలో తేమ (%)",
        "Rainfall (mm)": "వర్షపాతం (మి.మీ.)", "Fertilizer/NPK level": "ఎరువు/NPK స్థాయి", "Pest/disease severity (%)": "పురుగు/వ్యాధి తీవ్రత (%)",
        "Estimate Harvest": "కోత అంచనా వేయండి", "Your question": "మీ ప్రశ్న", "Describe what is happening in your field…": "మీ పొలంలో ఏమి జరుగుతుందో వివరించండి…",
        "Ask": "అడగండి", "Something went wrong. Please try again.": "ఏదో సమస్య వచ్చింది. దయచేసి మళ్లీ ప్రయత్నించండి.",
        "Could not get watering advice.": "నీటి సలహా పొందలేకపోయాం.", "Thank you for your feedback!": "మీ అభిప్రాయానికి ధన్యవాదాలు!",
        "Expected yield": "అంచనా దిగుబడి", "days old": "రోజుల వయస్సు", "days to typical harvest time": "సాధారణ కోత సమయానికి మిగిలిన రోజులు",
        "toward harvest readiness": "కోతకు సిద్ధమయ్యే పురోగతి", "YOUR FARM, AT A GLANCE": "మీ పొలం ఒక చూపులో",
        "days after planting": "నాటి రోజులు", "Home": "ప్రధాన పేజీ", "Error": "లోపం", "Live weather": "ప్రస్తుత వాతావరణం",
        "Loading weather...": "వాతావరణ సమాచారం లోడ్ అవుతోంది...", "Loading": "లోడ్ అవుతోంది", "planted": "నాటిన తేదీ:",
        "Rain expected - adjust irrigation accordingly": "వర్షం వచ్చే అవకాశం ఉంది - నీటి పారుదలని దానికి అనుగుణంగా మార్చండి",
        "Update crop": "పంట వివరాలను మార్చండి", "Weather unavailable": "వాతావరణ సమాచారం అందుబాటులో లేదు", "Weather updates": "వాతావరణ సమాచారం",
        "Your crop details": "మీ పంట వివరాలు", "Choose language": "భాషను ఎంచుకోండి",
        "Choose the language you are comfortable with.": "మీకు సౌకర్యంగా ఉండే భాషను ఎంచుకోండి.",
        "Choose your preferred language": "మీకు ఇష్టమైన భాషను ఎంచుకోండి", "Continue": "కొనసాగించండి",
        "Your Simple Farming Assistant": "మీ సరళమైన వ్యవసాయ సహాయకుడు", "Add optional details": "ఐచ్ఛిక వివరాలను జోడించండి",
        "Alluvial soil": "ఒండ్రు నేల", "Black soil": "నల్ల నేల", "Borewell": "బోరు బావి", "Canal": "కాలువ", "Choose a crop": "పంటను ఎంచుకోండి",
        "Coordinates added; please add your village or district for weather advice.": "స్థాన నిర్దేశాంకాలు జోడించబడ్డాయి; వాతావరణ సలహా కోసం మీ గ్రామం లేదా జిల్లాను జోడించండి.",
        "Could not get your location. Please type your village or district.": "మీ స్థానాన్ని పొందలేకపోయాం. దయచేసి మీ గ్రామం లేదా జిల్లాను నమోదు చేయండి.",
        "Crop variety": "పంట రకం", "Drip": "బిందు సేద్యం", "e.g. 2 acres": "ఉదా. 2 ఎకరాలు", "Farm size": "వ్యవసాయ భూమి విస్తీర్ణం",
        "Finding your location…": "మీ స్థానాన్ని కనుగొంటున్నాం…", "FIRST, YOUR CROP": "ముందుగా, మీ పంట", "Irrigation method": "నీటి పారుదల విధానం",
        "Location added. You can edit it if needed.": "స్థానం జోడించబడింది. అవసరమైతే మార్చవచ్చు.", "Location is not available in this browser.": "ఈ బ్రౌజర్‌లో స్థానం అందుబాటులో లేదు.",
        "Not sure / skip": "తెలియదు / దాటవేయండి", "Optional": "ఐచ్ఛికం", "Other": "ఇతర", "Rain-fed": "వర్షాధారం", "Red soil": "ఎర్ర నేల", "Your crop": "మీ పంట",
        "Required": "తప్పనిసరి", "Sandy soil": "ఇసుక నేల", "Soil type": "నేల రకం", "Sprinkler": "స్ప్రింక్లర్",
        "Tell us about your crop": "మీ పంట గురించి చెప్పండి", "This helps us tailor farming guidance to you.": "మీకు తగిన వ్యవసాయ సలహా అందించడానికి ఇది సహాయపడుతుంది.",
        "Use my location": "నా స్థానాన్ని ఉపయోగించండి", "Village, district, or area": "గ్రామం, జిల్లా లేదా ప్రాంతం", "What are you growing?": "మీరు ఏ పంట పండిస్తున్నారు?",
        "When did you plant it?": "ఎప్పుడు నాటారు?", "Where is your farm?": "మీ పొలం ఎక్కడ ఉంది?", "You can type your village or allow location access.": "మీ గ్రామం పేరు నమోదు చేయండి లేదా స్థాన అనుమతి ఇవ్వండి.",
        "Cotton": "పత్తి", "Paddy": "వరి", "Rice": "వరి", "Chilli": "మిరప", "Maize": "మొక్కజొన్న", "Wheat": "గోధుమ", "Sugarcane": "చెరకు",
        "Tomato": "టమాటా", "Potato": "బంగాళాదుంప", "Onion": "ఉల్లిపాయ", "Groundnut": "వేరుశెనగ", "Soybean": "సోయాబీన్", "Mustard": "ఆవాలు", "Sunflower": "పొద్దుతిరుగుడు", "Brinjal": "వంకాయ",
        "Take a clear photo of a leaf to check for possible problems.": "సమస్యలను గుర్తించడానికి ఆకును స్పష్టంగా ఫోటో తీయండి.",
        "Enter soil and nutrient details to check crop health.": "పంట ఆరోగ్యాన్ని తనిఖీ చేయడానికి నేల మరియు పోషకాల వివరాలను నమోదు చేయండి.",
        "Get irrigation advice based on current weather conditions.": "ప్రస్తుత వాతావరణ పరిస్థితుల ఆధారంగా నీటి పారుదల సలహా పొందండి.",
        "Enter crop observations to estimate harvest timing and yield.": "కోత సమయం మరియు దిగుబడిని అంచనా వేయడానికి పంట పరిశీలనలను నమోదు చేయండి.",
        "Describe your farming question and get help from FarmMitra.": "మీ వ్యవసాయ ప్రశ్నను వివరించి ఫార్మ్‌మిత్ర సహాయం పొందండి.",
        "Photo-based leaf check": "ఫోటో ద్వారా ఆకును తనిఖీ చేయండి", "Track your crop over time": "కాలక్రమంలో పంటను గమనించండి",
        "Simple irrigation guidance": "సరళమైన నీటి పారుదల సలహా", "Plan for harvest": "కోతకు ప్రణాళిక చేయండి", "Get help with a question": "మీ ప్రశ్నకు సహాయం పొందండి",
        "e.g., 45": "ఉదా., 45", "e.g., 7.1": "ఉదా., 7.1", "e.g., 1.1": "ఉదా., 1.1",
        "Farm not set up": "వ్యవసాయ వివరాలు నమోదు కాలేదు", "No image provided": "చిత్రం ఇవ్వలేదు", "Invalid feature": "చెల్లని ఎంపిక",
        "Enter valid soil moisture, pH, and EC measurements.": "నేల తేమ, pH మరియు EC విలువలను సరిగ్గా నమోదు చేయండి.",
        "No question provided": "ప్రశ్న నమోదు చేయలేదు", "Gemini API key not configured": "Gemini API కీ అమర్చలేదు",
        "Enter a valid soil moisture value.": "నేల తేమ విలువను సరిగ్గా నమోదు చేయండి.", "Soil moisture must be between 0 and 100%.": "నేల తేమ 0 నుంచి 100% మధ్య ఉండాలి.",
        "Irrigation Required": "నీరు పెట్టాలి", "Wait and Monitor": "వేచి గమనించండి", "Irrigate Soon": "త్వరలో నీరు పెట్టండి", "Water Soon": "త్వరలో నీరు పెట్టండి", "Do Not Irrigate": "నీరు పెట్టవద్దు", "Normal Conditions": "సాధారణ పరిస్థితులు",
        "Urgent": "అత్యవసరం", "Full": "పూర్తి", "Medium": "మధ్యస్థం",
        "Soil already has sufficient moisture. Additional watering may cause waterlogging.": "నేలలో తగినంత తేమ ఉంది. మరింత నీరు పెడితే నీరు నిలిచే ప్రమాదం ఉంది.",
        "Soil is dry and significant rainfall is not expected. Water soon, especially during flowering or fruit development.": "నేల పొడిగా ఉంది, గణనీయమైన వర్షం వచ్చే అవకాశం లేదు. ముఖ్యంగా పూత లేదా కాయల దశలో త్వరగా నీరు పెట్టండి.",
        "Soil moisture is adequate. No immediate irrigation is required. Continue monitoring.": "నేల తేమ సరిపడా ఉంది. వెంటనే నీరు పెట్టాల్సిన అవసరం లేదు. గమనిస్తూ ఉండండి.",
        "Soil is dry, but a high chance of rain is expected. Recheck soil moisture after rainfall.": "నేల పొడిగా ఉంది, కానీ వర్షం వచ్చే అవకాశం ఎక్కువగా ఉంది. వర్షం తర్వాత నేల తేమను మళ్లీ తనిఖీ చేయండి.",
        "Soil is dry. Rain may occur, so irrigate only as needed and monitor rainfall.": "నేల పొడిగా ఉంది. వర్షం పడవచ్చు కాబట్టి అవసరమైనంత మాత్రమే నీరు పెట్టి వర్షాన్ని గమనించండి.",
        "Soil moisture is getting low and high temperatures can increase water loss. Plan irrigation soon.": "నేల తేమ తగ్గుతోంది; అధిక ఉష్ణోగ్రత వల్ల నీరు త్వరగా ఆవిరవుతుంది. త్వరలో నీరు పెట్టేలా ప్రణాళిక చేయండి.",
        "Soil moisture is getting low. Plan irrigation depending on temperature and upcoming rainfall.": "నేల తేమ తగ్గుతోంది. ఉష్ణోగ్రత మరియు రాబోయే వర్షాన్ని బట్టి నీటి పారుదలను ప్రణాళిక చేయండి.",
        "Soil moisture is adequate and rain is likely. Wait and monitor soil conditions.": "నేల తేమ సరిపడా ఉంది మరియు వర్షం వచ్చే అవకాశం ఉంది. వేచి ఉండి నేల పరిస్థితిని గమనించండి.",
        "Recent rainfall is high. Avoid additional watering and monitor drainage.": "ఇటీవల ఎక్కువ వర్షం పడింది. అదనంగా నీరు పెట్టవద్దు; నీరు సరిగా బయటకు పోతుందో గమనించండి.",
        "Rain has fallen and more may be expected. Recheck soil moisture before watering.": "వర్షం పడింది, మరింత వర్షం రావచ్చు. నీరు పెట్టే ముందు నేల తేమను మళ్లీ తనిఖీ చేయండి.",
        "Current temperature:": "ప్రస్తుత ఉష్ణోగ్రత:",
        "Your ": "మీ ", " is ": " ", "% mature (": "% పక్వత (", "). Approximately ": "). సుమారు ", " days until harvest.": " రోజుల్లో కోతకు వస్తుంది.",
        "Estimated yield:": "అంచనా దిగుబడి:", " kg/acre.": " కిలోలు/ఎకరా.", " is estimated to be ": " పంట కోతకు సిద్ధమయ్యే అంచనా పురోగతి ",
        "Crop: ": "పంట: ", "Overall Health Score: ": "మొత్తం పంట ఆరోగ్య స్కోరు: ", "Health Status: ": "ఆరోగ్య స్థితి: ",
        "--- Detailed Scores ---": "--- వివరణాత్మక స్కోర్లు ---", "Soil Health Score: ": "నేల ఆరోగ్య స్కోరు: ",
        "Water Stress Score: ": "నీటి ఒత్తిడి స్కోరు: ", "Nutrient Score: ": "పోషకాల స్కోరు: ", "Weather Stress Score: ": "వాతావరణ ఒత్తిడి స్కోరు: ",
        "--- Risk Assessment ---": "--- ప్రమాద అంచనా ---", "Water Stress: ": "నీటి ఒత్తిడి: ", "Nutrient Stress: ": "పోషకాల ఒత్తిడి: ",
        "Environmental Stress: ": "పర్యావరణ ఒత్తిడి: ", "Overall Risk: ": "మొత్తం ప్రమాదం: ", "Issues detected:\n": "గుర్తించిన సమస్యలు:\n",
        "User reported: ": "రైతు తెలిపిన సమస్య: ", "Recommendations:\n": "సూచనలు:\n", "Excellent": "అద్భుతం", "Good": "మంచి", "Moderate": "మధ్యస్థం", "Poor": "బలహీనం", "Critical": "తీవ్రం",
        "High": "ఎక్కువ", "Very High": "చాలా ఎక్కువ", "Low soil moisture": "నేల తేమ తక్కువ", "Moderate soil moisture": "నేల తేమ మధ్యస్థంగా ఉంది",
        "High soil moisture - waterlogging risk": "నేల తేమ ఎక్కువ - నీరు నిలిచే ప్రమాదం", "Low rainfall": "వర్షపాతం తక్కువ", "Excessive rainfall": "అధిక వర్షపాతం",
        "Nitrogen deficiency": "నత్రజని లోపం", "Phosphorus deficiency": "భాస్వరం లోపం", "Potassium deficiency": "పొటాషియం లోపం",
        "Temperature stress": "ఉష్ణోగ్రత ఒత్తిడి", "Moderate temperature stress": "మధ్యస్థ ఉష్ణోగ్రత ఒత్తిడి", "Humidity stress": "గాలిలో తేమ వల్ల ఒత్తిడి", "Moderate humidity stress": "మధ్యస్థ తేమ ఒత్తిడి",
        "pH out of optimal range": "pH సరైన పరిధిలో లేదు", "pH slightly suboptimal": "pH కొద్దిగా సరైన పరిధికి బయట ఉంది", "High salinity (EC)": "లవణీయత ఎక్కువ (EC)", "Moderate salinity": "మధ్యస్థ లవణీయత",
        "Test soil pH and EC. Apply lime if acidic, gypsum if saline.": "నేల pH మరియు EC పరీక్షించండి. ఆమ్ల నేలకు సున్నం, లవణ నేలకు జిప్సం వేయండి.",
        "Adjust irrigation based on soil moisture. Ensure proper drainage.": "నేల తేమను బట్టి నీటి పారుదలను సర్దుబాటు చేయండి. నీరు సరిగా బయటకు వెళ్లేలా చూడండి.",
        "Conduct soil test. Apply fertilizers based on deficiency.": "నేల పరీక్ష చేయించి, లోపాన్ని బట్టి ఎరువులు వేయండి.",
        "Monitor weather conditions. Use shade nets or mulch if needed.": "వాతావరణాన్ని గమనించండి. అవసరమైతే నీడ వలలు లేదా మల్చ్ ఉపయోగించండి.",
        "Apply nitrogen fertilizer. Ensure proper spacing.": "నత్రజని ఎరువు వేయండి. మొక్కల మధ్య సరైన దూరం ఉంచండి.",
        "Monitor for nutrient deficiencies. Maintain irrigation.": "పోషకాల లోపాన్ని గమనించి, నీటి పారుదలను కొనసాగించండి.",
        "Reduce nitrogen, increase potassium. Protect from pests.": "నత్రజనిని తగ్గించి, పొటాషియాన్ని పెంచండి. పురుగుల నుంచి పంటను రక్షించండి.",
        "Ensure adequate moisture and protect from pests.": "తగినంత తేమ ఉండేలా చేసి, పురుగుల నుంచి పంటను రక్షించండి.",
        "Reduce irrigation. Prepare for harvest. Monitor moisture.": "నీటి పారుదలను తగ్గించండి. కోతకు సిద్ధం చేయండి. నేల తేమను గమనించండి.",
        "Farm not set up": "వ్యవసాయ వివరాలు నమోదు కాలేదు", "Submit soil moisture to get watering advice.": "నీటి సలహా పొందడానికి నేల తేమను నమోదు చేయండి.",
        "Enter crop and field details to estimate harvest.": "కోతను అంచనా వేయడానికి పంట మరియు పొలం వివరాలను నమోదు చేయండి.",
        "Complete all harvest fields with valid values.": "కోత అంచనా కోసం అన్ని వివరాలను సరిగ్గా నమోదు చేయండి.",
        "Planting date cannot be in the future.": "నాటిన తేదీ భవిష్యత్తులో ఉండకూడదు.", "Select valid growth stage and NPK level.": "సరైన ఎదుగుదల దశ మరియు NPK స్థాయిని ఎంచుకోండి.",
        "Moisture, humidity, and pest severity must be between 0 and 100.": "తేమ, గాలిలో తేమ మరియు పురుగు తీవ్రత 0 నుంచి 100 మధ్య ఉండాలి.",
        "Plant, fruit, and rainfall values cannot be negative.": "మొక్క, కాయ మరియు వర్షపాతం విలువలు ప్రతికూలంగా ఉండకూడదు.",
        "Analysis failed: ": "విశ్లేషణ విఫలమైంది: ", "TTS failed": "వాయిస్ తయారీ విఫలమైంది", "No image provided": "చిత్రం ఇవ్వలేదు",
        "No suitable Gemini model available": "తగిన Gemini మోడల్ అందుబాటులో లేదు", "Invalid feature": "చెల్లని ఎంపిక",
        "No question provided": "ప్రశ్న నమోదు చేయలేదు", "Missing required fields": "అవసరమైన వివరాలు నమోదు కాలేదు", "Analysis not found": "విశ్లేషణ కనబడలేదు"
        ,"Leaf disease detection analysis": "ఆకు వ్యాధి గుర్తింపు విశ్లేషణ",
        "Perform when you see spots, discoloration, or unusual patterns on leaves": "ఆకులపై మచ్చలు, రంగు మార్పు లేదా అసాధారణ ఆకృతులు కనిపించినప్పుడు తనిఖీ చేయండి",
        "Early detection prevents spread and protects yield": "ముందుగా గుర్తించడం వల్ల వ్యాధి వ్యాప్తి తగ్గి దిగుబడి రక్షించబడుతుంది",
        "Overall crop health assessment": "పంట మొత్తం ఆరోగ్య అంచనా", "Check weekly or when growth seems abnormal": "ప్రతి వారం లేదా ఎదుగుదల అసాధారణంగా ఉన్నప్పుడు తనిఖీ చేయండి",
        "Monitoring health helps optimize inputs and timing": "పంట ఆరోగ్యాన్ని గమనించడం వల్ల వనరులు మరియు సమయాన్ని మెరుగ్గా నిర్ణయించవచ్చు",
        "Irrigation recommendation": "నీటి పారుదల సిఫార్సు", "Check daily during critical growth stages": "ముఖ్యమైన ఎదుగుదల దశల్లో రోజూ తనిఖీ చేయండి",
        "Proper watering prevents stress and maximizes yield": "సరైన నీటి పారుదల ఒత్తిడిని తగ్గించి దిగుబడిని పెంచుతుంది",
        "Harvest timing estimation": "కోత సమయ అంచనా", "Monitor as crop approaches maturity": "పంట పక్వానికి చేరువయ్యే కొద్దీ గమనించండి",
        "Harvesting at optimal time ensures quality and market value": "సరైన సమయంలో కోయడం నాణ్యత మరియు మార్కెట్ విలువను కాపాడుతుంది",
        "Please enter a valid planting date.": "దయచేసి సరైన నాటిన తేదీని నమోదు చేయండి.", "Crop and farm location are required.": "పంట మరియు పొలం స్థానం తప్పనిసరి.",
        "Please choose a JPG, PNG, or WebP image.": "దయచేసి JPG, PNG లేదా WebP చిత్రాన్ని ఎంచుకోండి.", "Choose a photo first.": "ముందుగా ఫోటోను ఎంచుకోండి.",
        "No audio file provided": "ఆడియో ఫైల్ ఇవ్వలేదు", "TTS failed": "వాయిస్ తయారీ విఫలమైంది", "No image provided": "చిత్రం ఇవ్వలేదు",
        "Crop Recommendation": "పంట సిఫారసు",
        "AI Crop Recommendation": "AI పంట సిఫారసు",
        "Get AI-powered crop recommendation based on your location and current weather.": "మీ స్థానం మరియు వర్తమాన వాతావరణం ఆధారంగా AI పంట సిఫారసు పొందండి.",
        "Based on your location, current weather and soil, get the best crops to cultivate right now.": "మీ స్థానం, వాతావరణం మరియు నేల ఆధారంగా ఇప్పుడు పండించడానికి ఉత్తమ పంటలు పొందండి.",
        "Your farm location": "మీ పొలం స్థానం",
        "Soil type": "నేల రకం",
        "Irrigation": "నీటి పారుదల",
        "Not specified": "పేర్కొనలేదు",
        "Get Crop Recommendation": "పంట సిఫారసు పొందండి",
        "Send": "పంపు",
        "Record": "రికార్డు చేయి",
        "Stop": "ఆపు",
        "Auto-speak answer": "సమాధానం స్వయంగా చదవు",
        "Tap record, speak your farming question, then tap Stop and Send.": "రికార్డు నొక్కి, మీ వ్యవసాయ ప్రశ్న మాట్లాడి, ఆపు మరియు పంపు నొక్కండి.",
        "Speak using the mic above, or type your question here\u2026": "పై మైక్ ద్వారా మాట్లాడండి లేదా ఇక్కడ ప్రశ్న టైప్ చేయండి...",
        "Please type or speak a question first.": "ముందుగా ప్రశ్న టైప్ చేయండి లేదా మాట్లాడండి.",
        "Crop recommendation based on your location": "మీ స్థానం ఆధారంగా పంట సిఫారసు"
    }
}


def translate_text(text, target_lang):
    """Translate known UI and fixed advice phrases using local phrase rules only."""
    if target_lang == "en" or not text:
        return text
    rules = UI_RULES.get(target_lang, {})
    translated = rules.get(text)
    if translated is not None:
        return translated
    # Translate known phrases embedded in generated advice while preserving numbers/data.
    for source in sorted(rules, key=len, reverse=True):
        if source in text:
            text = text.replace(source, rules[source])
    return text


def text_to_speech(text, lang):
    """Convert text to speech and return as base64 audio"""
    if not GTTS_AVAILABLE:
        return None
    try:
        tts = gTTS(text=text, lang=lang)
        # Use unique filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        temp_filename = f"tts_{timestamp}.mp3"
        temp_path = Path(tempfile.gettempdir()) / temp_filename
        
        tts.save(str(temp_path))
        with open(temp_path, "rb") as audio_file:
            audio_data = audio_file.read()
        
        # Don't delete immediately - let OS clean up temp files
        # This avoids file locking issues with media players
            
        return base64.b64encode(audio_data).decode('utf-8')
    except Exception as e:
        print(f"TTS error: {e}")
        return None


def get_weather(location):
    """Get weather data using Open-Meteo API"""
    try:
        # Geocoding (simplified - using coordinates for demo)
        # In production, use a proper geocoding service
        coords = {"latitude": 17.385, "longitude": 78.4867}  # Default to Hyderabad
        
        # Build params with timezone (no format=flatbuffers)
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "current": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "forecast_days": 7,
            "timezone": "Asia/Kolkata"
        }
        
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        weather_data = {
            "current": {
                "temp": data["current"]["temperature_2m"],
                "humidity": data["current"]["relative_humidity_2m"],
                "precipitation": data["current"]["precipitation"],
                "rain_probability": data["current"].get("precipitation_probability", 0),
                "wind_speed": data["current"].get("wind_speed_10m", 0),
                "code": data["current"]["weather_code"]
            },
            "forecast": []
        }
        
        for i in range(len(data["daily"]["time"])):
            weather_data["forecast"].append({
                "date": data["daily"]["time"][i],
                "max_temp": data["daily"]["temperature_2m_max"][i],
                "min_temp": data["daily"]["temperature_2m_min"][i],
                "precipitation": data["daily"]["precipitation_sum"][i],
                "code": data["daily"]["weather_code"][i]
            })
        
        return weather_data
        
    except requests.RequestException as e:
        print(f"Weather API unavailable: {e}")
        # Return None to indicate service unavailable
        return None




def analyze_with_gemini(image_path, prompt, lang="en"):
    """Analyze image using Gemini Vision API"""
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            return {"error": "Gemini API key not configured"}
        
        # Get available model
        model_name = get_available_model()
        if not model_name:
            return {"error": "No suitable Gemini model available"}
        
        model = genai.GenerativeModel(model_name)
        
        # Load image
        img = Image.open(image_path)
        
        # Ask Gemini for the selected language directly; do not run a translator API.
        language_name = LANGUAGES.get(lang, "English")
        localized_prompt = f"{prompt}\nRespond entirely in {language_name}. Keep the response clear and farmer-friendly."
        response = model.generate_content([localized_prompt, img], stream=True)
        response.resolve()
        
        result_text = response.text if response.text else "Could not analyze image"
        
        return {"result": result_text, "confidence": 0.8}
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return {"error": f"Analysis failed: {str(e)}"}


def get_irrigation_advice(weather_data, soil_moisture, growth_stage="vegetative", lang="en"):
    """Return deterministic irrigation guidance from measured soil and current weather."""
    current = weather_data["current"] if weather_data else {}
    temp = float(current.get("temp") or 0)
    humidity = float(current.get("humidity") or 0)
    rain_probability = float(current.get("rain_probability") or 0)
    rainfall = float(current.get("precipitation") or 0)
    wind_speed = float(current.get("wind_speed") or 0)
    moisture = float(soil_moisture)

    if moisture > 60:
        advice, reason, priority = "Do Not Irrigate", "Soil already has sufficient moisture. Additional watering may cause waterlogging.", "Low"
    elif moisture < 25 and rain_probability > 70:
        advice, reason, priority = "Wait and Monitor", "Soil is dry, but a high chance of rain is expected. Recheck soil moisture after rainfall.", "Medium"
    elif moisture < 25 and rain_probability < 30:
        advice, reason, priority = "Irrigation Required", "Soil is dry and significant rainfall is not expected. Water soon, especially during flowering or fruit development.", "Urgent"
    elif moisture < 25:
        advice, reason, priority = "Irrigate Soon", "Soil is dry. Rain may occur, so irrigate only as needed and monitor rainfall.", "High"
    elif moisture < 40 and temp > 35:
        advice, reason, priority = "Water Soon", "Soil moisture is getting low and high temperatures can increase water loss. Plan irrigation soon.", "High"
    elif moisture < 40:
        advice, reason, priority = "Water Soon", "Soil moisture is getting low. Plan irrigation depending on temperature and upcoming rainfall.", "Medium"
    elif rain_probability > 60:
        advice, reason, priority = "Do Not Irrigate", "Soil moisture is adequate and rain is likely. Wait and monitor soil conditions.", "Low"
    else:
        advice, reason, priority = "Normal Conditions", "Soil moisture is adequate. No immediate irrigation is required. Continue monitoring.", "Low"

    if rainfall > 15:
        advice, reason, priority = "Do Not Irrigate", "Recent rainfall is high. Avoid additional watering and monitor drainage.", "Low"
    elif rainfall >= 2 and moisture < 40 and rain_probability >= 20:
        advice, reason = "Wait and Monitor", "Rain has fallen and more may be expected. Recheck soil moisture before watering."

    # A transparent heuristic score: dry soil drives the score; hot, windy weather
    # raises urgency, while likely rain lowers it.
    score = max(0, min(100, (60 - moisture) * 1.5 + max(0, temp - 30) * 2 + max(0, wind_speed - 10) * 0.5 - rain_probability * 0.3 - rainfall * 2))
    if growth_stage.lower() in ("flowering", "fruiting") and moisture < 40:
        score = min(100, score + 10)
    if moisture > 60 or rainfall > 15 or (moisture < 25 and rain_probability > 70):
        score = min(score, 20)

    if lang != "en":
        advice, reason = translate_text(advice, lang), translate_text(reason, lang)
    return {
        "advice": advice, "reason": reason, "priority": priority,
        "water_stress_score": round(score),
        "conditions": {
            "soil_moisture": moisture, "temperature": temp, "humidity": humidity,
            "rain_probability": rain_probability, "rainfall": rainfall,
            "wind_speed": wind_speed, "growth_stage": growth_stage
        }
    }


def check_crop_health(weather_data, crop, age_days, soil_moisture, soil_ph, nitrogen, phosphorus, potassium, ec, user_issues, lang="en"):
    """Check crop health using multi-score system"""
    crop_lower = crop.lower()
    
    # 1. Soil Health Score (pH + EC)
    soil_score = 100
    soil_issues = []
    
    # pH scoring
    if soil_ph < 5.5 or soil_ph > 8.5:
        soil_score -= 25
        soil_issues.append("pH out of optimal range")
    elif soil_ph < 6.0 or soil_ph > 8.0:
        soil_score -= 10
        soil_issues.append("pH slightly suboptimal")
    
    # EC scoring
    if ec > 4:
        soil_score -= 25
        soil_issues.append("High salinity (EC)")
    elif ec > 2:
        soil_score -= 10
        soil_issues.append("Moderate salinity")
    
    soil_score = max(0, soil_score)
    
    # 2. Water Stress Score (soil moisture + rainfall)
    water_score = 100
    water_issues = []
    
    # Soil moisture scoring
    if soil_moisture < 25:
        water_score -= 35
        water_issues.append("Low soil moisture")
    elif soil_moisture < 40:
        water_score -= 15
        water_issues.append("Moderate soil moisture")
    elif soil_moisture > 60:
        water_score -= 15
        water_issues.append("High soil moisture - waterlogging risk")
    
    # Rainfall impact
    if weather_data:
        precip = weather_data["current"]["precipitation"]
        if precip < 1 and age_days > 14:
            water_score -= 20
            water_issues.append("Low rainfall")
        elif precip > 50:
            water_score -= 20
            water_issues.append("Excessive rainfall")
    
    water_score = max(0, water_score)
    
    # 3. Nutrient Score (N + P + K)
    nutrient_score = 100
    nutrient_issues = []
    
    nutrient_map = {"low": 30, "medium": 15, "adequate": 0}
    nutrient_score -= nutrient_map.get(nitrogen, 0)
    nutrient_score -= nutrient_map.get(phosphorus, 0)
    nutrient_score -= nutrient_map.get(potassium, 0)
    
    if nitrogen == "low":
        nutrient_issues.append("Nitrogen deficiency")
    if phosphorus == "low":
        nutrient_issues.append("Phosphorus deficiency")
    if potassium == "low":
        nutrient_issues.append("Potassium deficiency")
    
    nutrient_score = max(0, nutrient_score)
    
    # 4. Weather Stress Score (temperature + humidity)
    weather_score = 100
    weather_issues = []
    
    if weather_data:
        temp = weather_data["current"]["temp"]
        humidity = weather_data["current"]["humidity"]
        
        # Temperature scoring
        if temp < 18 or temp > 38:
            weather_score -= 35
            weather_issues.append("Temperature stress")
        elif temp < 22 or temp > 35:
            weather_score -= 15
            weather_issues.append("Moderate temperature stress")
        
        # Humidity scoring
        if humidity < 35 or humidity > 85:
            weather_score -= 35
            weather_issues.append("Humidity stress")
        elif humidity < 50 or humidity > 75:
            weather_score -= 15
            weather_issues.append("Moderate humidity stress")
    
    weather_score = max(0, weather_score)
    
    # Overall Health Score (weighted average)
    overall_score = (soil_score * 0.25 + water_score * 0.25 + nutrient_score * 0.25 + weather_score * 0.25)
    overall_score = round(overall_score, 1)
    
    # Determine status
    if overall_score >= 90:
        status = "Excellent"
        risk_level = "Low"
    elif overall_score >= 75:
        status = "Good"
        risk_level = "Low"
    elif overall_score >= 50:
        status = "Moderate"
        risk_level = "Medium"
    elif overall_score >= 25:
        status = "Poor"
        risk_level = "High"
    else:
        status = "Critical"
        risk_level = "Very High"
    
    # Build result
    result = f"Crop: {crop}\n"
    result += f"Overall Health Score: {overall_score}/100\n"
    result += f"Health Status: {status}\n\n"
    result += f"--- Detailed Scores ---\n"
    result += f"Soil Health Score: {soil_score}/100\n"
    result += f"Water Stress Score: {water_score}/100\n"
    result += f"Nutrient Score: {nutrient_score}/100\n"
    result += f"Weather Stress Score: {weather_score}/100\n\n"
    result += f"--- Risk Assessment ---\n"
    result += f"Water Stress: {risk_level if water_score < 70 else 'Low'}\n"
    result += f"Nutrient Stress: {risk_level if nutrient_score < 70 else 'Low'}\n"
    result += f"Environmental Stress: {risk_level if weather_score < 70 else 'Low'}\n"
    result += f"Overall Risk: {risk_level}\n\n"
    
    all_issues = soil_issues + water_issues + nutrient_issues + weather_issues
    if all_issues:
        result += f"Issues detected:\n" + "\n".join(f"- {issue}" for issue in all_issues) + "\n\n"
    
    if user_issues:
        result += f"User reported: {user_issues}\n\n"
    
    # Recommendations based on scores
    recommendations = []
    if soil_score < 70:
        recommendations.append("Test soil pH and EC. Apply lime if acidic, gypsum if saline.")
    if water_score < 70:
        recommendations.append("Adjust irrigation based on soil moisture. Ensure proper drainage.")
    if nutrient_score < 70:
        recommendations.append("Conduct soil test. Apply fertilizers based on deficiency.")
    if weather_score < 70:
        recommendations.append("Monitor weather conditions. Use shade nets or mulch if needed.")
    
    if recommendations:
        result += "Recommendations:\n" + "\n".join(f"- {rec}" for rec in recommendations)
    
    if lang != "en":
        result = translate_text(result, lang)
    
    return {
        "health_score": overall_score,
        "status": status,
        "soil_score": soil_score,
        "water_score": water_score,
        "nutrient_score": nutrient_score,
        "weather_score": weather_score,
        "risk_level": risk_level,
        "issues": all_issues,
        "result": result
    }


def get_maturity_estimate(crop, age_days, lang="en"):
    """Estimate crop maturity based on crop type and age"""
    crop_lower = crop.lower()
    maturity_days = CROP_MATURITY.get(crop_lower, 100)
    
    progress = min(100, (age_days / maturity_days) * 100)
    days_remaining = max(0, maturity_days - age_days)
    
    # Rule-based stage determination
    if progress < 20:
        stage = "Seedling establishment"
        care_tip = "Ensure adequate moisture and protect from pests."
    elif progress < 40:
        stage = "Vegetative growth"
        care_tip = "Apply nitrogen fertilizer. Ensure proper spacing."
    elif progress < 60:
        stage = "Active growth phase"
        care_tip = "Monitor for nutrient deficiencies. Maintain irrigation."
    elif progress < 80:
        stage = "Flowering/fruiting"
        care_tip = "Reduce nitrogen, increase potassium. Protect from pests."
    else:
        stage = "Maturation/Harvest ready"
        care_tip = "Reduce irrigation. Prepare for harvest. Monitor moisture."
    
    estimate = f"Your {crop} is {progress:.1f}% mature ({stage}). Approximately {days_remaining} days until harvest.\n\nCare tip: {care_tip}"
    
    if lang != "en":
        estimate = translate_text(estimate, lang)
    
    return {"progress": progress, "stage": stage, "days_remaining": days_remaining, "estimate": estimate}


def estimate_harvest(data):
    """Estimate harvest timing and yield from farmer-entered crop observations."""
    crop = data["crop"].strip().lower()
    maturity_days = CROP_MATURITY.get(crop, 100)
    sowing_date = date.fromisoformat(data["planting_date"])
    age_days = max(0, (date.today() - sowing_date).days)
    maturity_progress = min(100, age_days / maturity_days * 100)

    base_yield = {
        "cotton": 700, "paddy": 2200, "rice": 2200, "chilli": 1200,
        "maize": 2500, "wheat": 1600, "sugarcane": 30000, "tomato": 10000,
        "potato": 8000, "onion": 7000, "groundnut": 900, "soybean": 1000,
        "mustard": 700, "sunflower": 700, "brinjal": 8000
    }.get(crop, 1000)

    # Scale the crop's reference yield using reported plant development and conditions.
    structure = min(1.15, max(0.65, data["plant_height"] / 100))
    branching = min(1.10, max(0.80, 0.8 + data["branches"] / 100))
    fruiting = min(1.15, max(0.60, 0.6 + data["fruit_count"] / 100))
    size_factor = min(1.10, max(0.75, 0.75 + data["fruit_size"] / 20))
    moisture_factor = 1.0 if 25 <= data["soil_moisture"] <= 60 else 0.85
    temperature_factor = 1.0 if 18 <= data["temperature"] <= 35 else 0.88
    humidity_factor = 1.0 if 40 <= data["humidity"] <= 75 else 0.95
    rainfall_factor = 1.0 if 2 <= data["rainfall"] <= 15 else (0.90 if data["rainfall"] == 0 else 0.92)
    nutrient_factor = {"low": 0.75, "medium": 0.90, "adequate": 1.0}[data["npk"]]
    pest_factor = max(0.40, 1 - data["pest_severity"] / 100)
    yield_estimate = round(base_yield * structure * branching * fruiting * size_factor * moisture_factor * temperature_factor * humidity_factor * rainfall_factor * nutrient_factor * pest_factor)

    stage_progress = {"vegetative": 25, "flowering": 55, "fruiting": 80, "maturity": 100}[data["growth_stage"]]
    progress = round(min(100, maturity_progress * 0.6 + stage_progress * 0.4), 1)
    days_remaining = max(0, maturity_days - age_days)
    return {
        "crop": data["crop"], "age_days": age_days,
        "growth_stage": data["growth_stage"].title(),
        "progress": progress, "days_remaining": days_remaining,
        "yield_kg_per_acre": yield_estimate,
        "estimate": f"{data['crop'].title()} is estimated to be {progress}% toward harvest readiness. Estimated yield: {yield_estimate} kg/acre."
    }


def decision_engine(feature, data, lang="en"):
    """Generate explainable decision with What/When/Why"""
    decisions = {
        "leaf": {
            "what": "Leaf disease detection analysis",
            "when": "Perform when you see spots, discoloration, or unusual patterns on leaves",
            "why": "Early detection prevents spread and protects yield"
        },
        "health": {
            "what": "Overall crop health assessment",
            "when": "Check weekly or when growth seems abnormal",
            "why": "Monitoring health helps optimize inputs and timing"
        },
        "water": {
            "what": "Irrigation recommendation",
            "when": "Check daily during critical growth stages",
            "why": "Proper watering prevents stress and maximizes yield"
        },
        "harvest": {
            "what": "Harvest timing estimation",
            "when": "Monitor as crop approaches maturity",
            "why": "Harvesting at optimal time ensures quality and market value"
        }
    }
    
    decision = decisions.get(feature, {})
    if lang != "en":
        decision = {k: translate_text(v, lang) for k, v in decision.items()}
    
    return decision


def recommend_crop(location, lang="en"):
    """Recommend suitable crop based on location and weather conditions"""
    weather_data = get_weather(location)
    
    if not weather_data:
        return {"error": "Weather data not available for crop recommendation"}
    
    temp = weather_data["current"]["temp"]
    humidity = weather_data["current"]["humidity"]
    precip = weather_data["current"]["precipitation"]
    current_month = datetime.now().month
    
    # Crop suitability rules based on conditions
    suitable_crops = []
    
    # Cotton: Warm, moderate humidity
    if 25 <= temp <= 35 and 40 <= humidity <= 70 and current_month in [4, 5, 6]:
        suitable_crops.append({
            "crop": "Cotton",
            "suitability": "High",
            "reason": f"Temperature ({temp}°C) is ideal for cotton germination. Moderate humidity ({humidity}%) prevents fungal issues. April-June is optimal planting season."
        })
    
    # Rice: Warm, high humidity, high rainfall
    if 25 <= temp <= 32 and humidity >= 70 and current_month in [6, 7, 8]:
        suitable_crops.append({
            "crop": "Rice",
            "suitability": "High",
            "reason": f"High humidity ({humidity}%) and warm temperature ({temp}°C) are perfect for rice. Monsoon season (Jun-Aug) provides adequate water."
        })
    
    # Wheat: Cool to moderate
    if 15 <= temp <= 25 and current_month in [10, 11, 12]:
        suitable_crops.append({
            "crop": "Wheat",
            "suitability": "High",
            "reason": f"Moderate temperature ({temp}°C) is ideal for wheat growth. Winter season (Oct-Dec) prevents heat stress."
        })
    
    # Maize: Warm, moderate conditions
    if 20 <= temp <= 30 and 50 <= humidity <= 80 and current_month in [6, 7, 8]:
        suitable_crops.append({
            "crop": "Maize",
            "suitability": "High",
            "reason": f"Temperature ({temp}°C) and humidity ({humidity}%) support maize growth. Kharif season is suitable."
        })
    
    # Tomato: Moderate temperature
    if 18 <= temp <= 28 and 50 <= humidity <= 70:
        suitable_crops.append({
            "crop": "Tomato",
            "suitability": "Medium",
            "reason": f"Moderate temperature ({temp}°C) is good for tomato. Can be grown in multiple seasons with proper care."
        })
    
    # Potato: Cool to moderate
    if 15 <= temp <= 25 and humidity <= 70:
        suitable_crops.append({
            "crop": "Potato",
            "suitability": "Medium",
            "reason": f"Cool to moderate temperature ({temp}°C) prevents tuber diseases. Low humidity reduces rot risk."
        })
    
    if not suitable_crops:
        return {
            "crop": "None recommended",
            "suitability": "Low",
            "reason": f"Current conditions (Temp: {temp}°C, Humidity: {humidity}%) are not optimal for major crops. Consider soil improvement or wait for better season."
        }
    
    # Return top recommendation
    top_crop = suitable_crops[0]
    result = f"Recommended Crop: {top_crop['crop']}\nSuitability: {top_crop['suitability']}\n\nWhy it's suitable:\n{top_crop['reason']}"
    
    if lang != "en":
        result = translate_text(result, lang)
    
    return {"crop": top_crop["crop"], "suitability": top_crop["suitability"], "reason": top_crop["reason"], "result": result}


@app.context_processor
def inject_common():
    lang = session.get("language", "en")
    return {"languages": LANGUAGES, "language": lang, "t": TEXT.get(lang, TEXT["en"]), "farm": get_farm(), "tr": lambda text: translate_text(text, lang)}


@app.after_request
def translate_api_errors(response):
    """Keep user-facing API errors in the currently selected language."""
    lang = session.get("language", "en")
    if lang != "en" and response.is_json:
        payload = response.get_json(silent=True)
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            payload["error"] = translate_text(payload["error"], lang)
            response.set_data(jsonify(payload).get_data())
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    farm = get_farm()
    if not session.get("language"):
        return redirect(url_for("language"))
    if not farm:
        return redirect(url_for("setup"))
    age = max(0, (date.today() - date.fromisoformat(farm["sowing_date"])).days)
    return render_template("home.html", age=age)


@app.route("/language", methods=["GET", "POST"])
def language():
    if request.method == "POST":
        session["language"] = request.form.get("language", "en")
        session["first_visit"] = True
        return redirect(url_for("setup") if not get_farm() else url_for("loading"))
    return render_template("language.html")


@app.route("/loading")
def loading():
    """Show loading page for 3 seconds before redirecting to home"""
    if not session.get("language"):
        return redirect(url_for("language"))
    if not get_farm():
        return redirect(url_for("setup"))
    return render_template("loading.html")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    lang = session.get("language", "en")
    
    if request.method == "POST":
        crop, sowing_date, location = (request.form.get(k, "").strip() for k in ("crop", "sowing_date", "location"))
        try:
            date.fromisoformat(sowing_date)
        except ValueError:
            flash("Please enter a valid planting date.", "error")
            return render_template("setup.html")
        if not crop or not location:
            flash("Crop and farm location are required.", "error")
            return render_template("setup.html")
        with db() as conn:
            conn.execute("INSERT INTO farm(crop,variety,sowing_date,location,farm_size,soil_type,irrigation,created_at) VALUES(?,?,?,?,?,?,?,?)",
                         (crop, request.form.get("variety", "").strip(), sowing_date, location,
                          request.form.get("farm_size", "").strip(), request.form.get("soil_type", "").strip(),
                          request.form.get("irrigation", "").strip(), datetime.now().isoformat(timespec="seconds")))
        return redirect(url_for("loading"))
    
    # GET request - provide crop recommendation if location is provided
    location = request.args.get("location", "")
    recommendation = None
    if location:
        recommendation = recommend_crop(location, lang)
    
    return render_template("setup.html", recommendation=recommendation)


FEATURES = {
    "leaf": ("🍃", "leaf", "Check My Leaf", "Take a clear photo of a leaf to check for possible problems."),
    "health": ("🌱", "health", "Check Crop Health", "Enter soil and nutrient details to check crop health."),
    "water": ("💧", "water", "Watering Advice", "Get irrigation advice based on current weather conditions."),
    "harvest": ("🌾", "harvest", "Harvest Estimate", "Enter crop observations to estimate harvest timing and yield."),
    "ask": ("🎙️", "ask", "Ask FarmMitra", "Describe your farming question and get help from FarmMitra."),
    "recommend": ("🌾🤖", "recommend", "Crop Recommendation", "Get AI-powered crop recommendation based on your location and current weather."),
}

# Guided form question configurations
GUIDED_FORM_QUESTIONS = {
    "health": [
        {"key": "soil_moisture", "type": "number", "min": 0, "max": 100, "step": 0.1, "placeholder": "e.g., 45", "required": True},
        {"key": "soil_ph", "type": "number", "min": 0, "max": 14, "step": 0.1, "placeholder": "e.g., 7.1", "required": True},
        {"key": "nitrogen", "type": "select", "options": [{"value": "low", "label": "Low"}, {"value": "medium", "label": "Medium"}, {"value": "adequate", "label": "Adequate"}], "required": True},
        {"key": "phosphorus", "type": "select", "options": [{"value": "low", "label": "Low"}, {"value": "medium", "label": "Medium"}, {"value": "adequate", "label": "Adequate"}], "required": True},
        {"key": "potassium", "type": "select", "options": [{"value": "low", "label": "Low"}, {"value": "medium", "label": "Medium"}, {"value": "adequate", "label": "Adequate"}], "required": True},
        {"key": "ec", "type": "number", "min": 0, "max": 10, "step": 0.1, "placeholder": "e.g., 1.1", "required": True},
        {"key": "issues", "type": "textarea", "placeholder": "Describe any problems (yellowing, spots, wilting, etc.)", "required": False},
    ],
    "water": [
        {"key": "soil_moisture", "type": "number", "min": 0, "max": 100, "step": 0.1, "placeholder": "e.g., 28", "required": True},
        {"key": "growth_stage", "type": "select", "options": [{"value": "vegetative", "label": "Vegetative"}, {"value": "flowering", "label": "Flowering"}, {"value": "fruiting", "label": "Fruit development"}], "required": True},
    ],
    "harvest": [
        {"key": "crop", "type": "select", "options": [{"value": "Cotton", "label": "Cotton"}, {"value": "Paddy", "label": "Paddy"}, {"value": "Chilli", "label": "Chilli"}, {"value": "Maize", "label": "Maize"}, {"value": "Wheat", "label": "Wheat"}, {"value": "Sugarcane", "label": "Sugarcane"}, {"value": "Tomato", "label": "Tomato"}, {"value": "Potato", "label": "Potato"}, {"value": "Onion", "label": "Onion"}, {"value": "Groundnut", "label": "Groundnut"}, {"value": "Soybean", "label": "Soybean"}, {"value": "Mustard", "label": "Mustard"}, {"value": "Sunflower", "label": "Sunflower"}, {"value": "Brinjal", "label": "Brinjal"}], "required": True},
        {"key": "planting_date", "type": "date", "required": True},
        {"key": "growth_stage", "type": "select", "options": [{"value": "vegetative", "label": "Vegetative"}, {"value": "flowering", "label": "Flowering"}, {"value": "fruiting", "label": "Fruiting"}, {"value": "maturity", "label": "Maturity"}], "required": True},
        {"key": "plant_height", "type": "number", "min": 0, "step": 0.1, "placeholder": "Height in cm", "required": True},
        {"key": "branches", "type": "number", "min": 0, "step": 1, "placeholder": "Number of branches", "required": True},
        {"key": "fruit_count", "type": "number", "min": 0, "step": 1, "placeholder": "Number of fruits/bolls", "required": True},
        {"key": "fruit_size", "type": "number", "min": 0, "step": 0.1, "placeholder": "Size in cm", "required": True},
        {"key": "soil_moisture", "type": "number", "min": 0, "max": 100, "step": 0.1, "placeholder": "Moisture %", "required": True},
        {"key": "temperature", "type": "number", "step": 0.1, "placeholder": "Temperature °C", "required": True},
        {"key": "humidity", "type": "number", "min": 0, "max": 100, "step": 0.1, "placeholder": "Humidity %", "required": True},
        {"key": "rainfall", "type": "number", "min": 0, "step": 0.1, "placeholder": "Rainfall mm", "required": True},
        {"key": "npk", "type": "select", "options": [{"value": "low", "label": "Low"}, {"value": "medium", "label": "Medium"}, {"value": "adequate", "label": "Adequate"}], "required": True},
        {"key": "pest_severity", "type": "number", "min": 0, "max": 100, "step": 1, "placeholder": "Severity %", "required": True},
    ],
}


def get_guided_questions(feature_name, lang):
    """Get guided form questions with translated text"""
    questions = GUIDED_FORM_QUESTIONS.get(feature_name, [])
    text = TEXT.get(lang, TEXT["en"])
    
    # Map question keys to translation keys
    question_map = {
        "soil_moisture": ("q_soil_moisture", "q_soil_moisture_desc"),
        "soil_ph": ("q_soil_ph", "q_soil_ph_desc"),
        "nitrogen": ("q_nitrogen", "q_nitrogen_desc"),
        "phosphorus": ("q_phosphorus", "q_phosphorus_desc"),
        "potassium": ("q_potassium", "q_potassium_desc"),
        "ec": ("q_ec", "q_ec_desc"),
        "issues": ("q_issues", "q_issues_desc"),
        "growth_stage": ("q_growth_stage", "q_growth_stage_desc"),
        "crop": ("q_crop_type", "q_crop_type_desc"),
        "planting_date": ("q_planting_date", "q_planting_date_desc"),
        "plant_height": ("q_plant_height", "q_plant_height_desc"),
        "branches": ("q_branches", "q_branches_desc"),
        "fruit_count": ("q_fruit_count", "q_fruit_count_desc"),
        "fruit_size": ("q_fruit_size", "q_fruit_size_desc"),
        "temperature": ("q_temperature", "q_temperature_desc"),
        "humidity": ("q_humidity", "q_humidity_desc"),
        "rainfall": ("q_rainfall", "q_rainfall_desc"),
        "npk": ("q_npk", "q_npk_desc"),
        "pest_severity": ("q_pest_severity", "q_pest_severity_desc"),
    }
    
    # Translate select options
    option_map = {
        "low": "Low",
        "medium": "Medium", 
        "adequate": "Adequate",
        "vegetative": "Vegetative",
        "flowering": "Flowering",
        "fruiting": "Fruiting",
        "maturity": "Maturity",
    }
    
    translated_questions = []
    for q in questions:
        translated_q = q.copy()
        if q["key"] in question_map:
            title_key, desc_key = question_map[q["key"]]
            translated_q["text"] = text.get(title_key, title_key)
            translated_q["description"] = text.get(desc_key, desc_key)
        
        # Translate select options
        if "options" in translated_q:
            translated_q["options"] = []
            for opt in q["options"]:
                translated_opt = opt.copy()
                translated_opt["label"] = text.get(opt["label"].lower().replace(" ", "_"), opt["label"])
                translated_q["options"].append(translated_opt)
        
        translated_questions.append(translated_q)
    
    return translated_questions


@app.route("/feature/<name>", methods=["GET", "POST"])
def feature(name):
    if name not in FEATURES:
        return redirect(url_for("index"))
    
    # Use guided form for health, water, and harvest
    if name in ["health", "water", "harvest"]:
        farm = get_farm()
        if not farm and name != "harvest":
            flash("Farm not set up. Please set up your farm first.", "error")
            return redirect(url_for("setup"))
        
        lang = session.get("language", "en")
        icon, key, title, description = FEATURES[name]
        
        # Get translated questions
        questions = get_guided_questions(name, lang)
        
        # Translate select option labels
        text = TEXT.get(lang, TEXT["en"])
        for q in questions:
            if "options" in q:
                for opt in q["options"]:
                    if opt["label"] in ["Low", "Medium", "Adequate"]:
                        opt["label"] = text.get(opt["label"].lower(), opt["label"])
                    elif opt["label"] in ["Vegetative", "Flowering", "Fruiting", "Maturity"]:
                        opt["label"] = text.get(opt["label"].lower().replace(" ", "_"), opt["label"])
        
        return render_template(
            "guided_form.html",
            icon=icon,
            title=TEXT.get(lang, TEXT["en"])[key],
            description=translate_text(description, lang),
            name=name,
            language=lang,
            total_steps=len(questions),
            questions=questions
        )
    
    # Original feature.html for leaf, ask, recommend
    if request.method == "POST":
        file = request.files.get("photo")
        if file and file.filename:
            safe = secure_filename(file.filename)
            if Path(safe).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                flash("Please choose a JPG, PNG, or WebP image.", "error")
            else:
                file.save(UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe}")
                flash("Photo saved. AI analysis will be available after Gemini is connected.", "success")
        else:
            flash("Choose a photo first.", "error")
        return redirect(url_for("feature", name=name))
    farm = get_farm()
    age = max(0, (date.today() - date.fromisoformat(farm["sowing_date"])).days) if farm else 0
    icon, key, title, description = FEATURES[name]
    lang = session.get("language", "en")
    return render_template("feature.html", icon=icon, title=TEXT.get(lang, TEXT["en"])[key], description=translate_text(description, lang), name=name, age=age)


@app.route("/reset", methods=["POST"])
def reset():
    with db() as conn:
        conn.execute("DELETE FROM farm")
    return redirect(url_for("loading"))


# API Endpoints for voice and features

@app.route("/api/speech-to-text", methods=["POST"])
def speech_to_text():
    """Convert speech audio to text using Gemini (handles webm/ogg from browser)"""
    lang = session.get("language", "en")
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    # Detect mime type from content-type or filename
    content_type = audio_file.content_type or "audio/webm"
    if "ogg" in content_type:
        suffix = ".ogg"
        mime = "audio/ogg"
    elif "wav" in content_type:
        suffix = ".wav"
        mime = "audio/wav"
    elif "mp4" in content_type or "m4a" in content_type:
        suffix = ".m4a"
        mime = "audio/mp4"
    else:
        suffix = ".webm"
        mime = "audio/webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
        audio_file.save(fp.name)
        tmp_path = fp.name

    try:
        answer_language = LANGUAGES.get(lang, "English")
        model = genai.GenerativeModel('gemini-2.5-flash')
        with open(tmp_path, "rb") as af:
            audio_data_bytes = af.read()

        audio_part = {"mime_type": mime, "data": audio_data_bytes}
        prompt = f"Transcribe this {answer_language} speech. Return only the text."
        response = model.generate_content([prompt, audio_part])
        text = response.text.strip() if response.text else ""
        os.unlink(tmp_path)
        if text:
            return jsonify({"text": text})
        else:
            return jsonify({"error": "Could not transcribe audio"}), 400
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/text-to-speech", methods=["POST"])
def api_text_to_speech():
    """Convert text to speech and return audio"""
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", session.get("language", "en"))
    
    audio_base64 = text_to_speech(text, lang)
    if audio_base64:
        return jsonify({"audio": audio_base64})
    else:
        return jsonify({"error": "TTS failed"}), 500


@app.route("/api/weather")
def api_weather():
    """Get weather data for current location"""
    farm = get_farm()
    if not farm:
        return jsonify({"error": "Farm not set up"}), 400
    
    lang = session.get("language", "en")
    weather_data = get_weather(farm["location"])
    
    if weather_data:
        # Translate weather descriptions
        if lang != "en":
            weather_data["description"] = translate_text(f"Current temperature: {weather_data['current']['temp']:.1f}°C", lang)
        else:
            weather_data["description"] = f"Current temperature: {weather_data['current']['temp']:.1f}°C"
        return jsonify(weather_data)
    else:
        # Return user-friendly error message
        error_msg = "Weather temporarily unavailable. Please try again in a moment."
        return jsonify({"error": error_msg, "unavailable": True}), 503


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Analyze image (leaf) or check crop health (no image needed)"""
    lang = session.get("language", "en")
    feature = request.form.get("feature", "leaf")
    
    # For crop health, no image needed - use rule-based system
    if feature == "health":
        farm = get_farm()
        if not farm:
            return jsonify({"error": "Farm not set up"}), 400
        
        weather_data = get_weather(farm["location"])
        age = max(0, (date.today() - date.fromisoformat(farm["sowing_date"])).days)
        
        # These measurements are submitted by the crop health form.
        try:
            soil_moisture = float(request.form["soil_moisture"])
            soil_ph = float(request.form["soil_ph"])
            ec = float(request.form["ec"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "Enter valid soil moisture, pH, and EC measurements."}), 400

        nitrogen = request.form.get("nitrogen", "medium")
        phosphorus = request.form.get("phosphorus", "medium")
        potassium = request.form.get("potassium", "medium")
        user_issues = request.form.get("issues", "")

        result = check_crop_health(
            weather_data, farm["crop"], age, soil_moisture, soil_ph,
            nitrogen, phosphorus, potassium, ec, user_issues, lang
        )
        
        with db() as conn:
            conn.execute(
                "INSERT INTO analyses(feature, image_path, result, confidence, language, created_at) VALUES(?,?,?,?,?,?)",
                (feature, "", result["result"], result["health_score"] / 100, lang, datetime.now().isoformat(timespec="seconds"))
            )
        
        return jsonify(result)
    
    # For leaf disease, image is required - use Gemini API
    if feature == "leaf":
        if "photo" not in request.files:
            return jsonify({"error": "No image provided"}), 400
        
        file = request.files["photo"]
        if file.filename:
            safe = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
            image_path = UPLOAD_DIR / f"{timestamp}_{safe}"
            file.save(str(image_path))
            
            answer_language = LANGUAGES.get(lang, "English")
            prompt = (
                f"Analyze this leaf in {answer_language}. SHORT format:\n\n"
                f"**1. Leaf Status**\n"
                f"1 sentence.\n\n"
                f"**2. Possible Problem**\n"
                f"1-2 lines. Say if not a leaf.\n\n"
                f"**3. Recommended Actions**\n"
                f"- Action 1\n"
                f"- Action 2\n\n"
                f"**4. Prevention**\n"
                f"- Tip 1\n"
                f"- Tip 2\n\n"
                f"**5. Confidence**\n"
                f"High/Medium/Low. Limitations: image-based only."
            )
            result = analyze_with_gemini(str(image_path), prompt, lang)
            
            if "error" not in result:
                with db() as conn:
                    conn.execute(
                        "INSERT INTO analyses(feature, image_path, result, confidence, language, created_at) VALUES(?,?,?,?,?,?)",
                        (feature, str(image_path), result["result"], result.get("confidence", 0), lang, datetime.now().isoformat(timespec="seconds"))
                    )
            
            return jsonify(result)
    
    return jsonify({"error": "Invalid feature"}), 400


@app.route("/api/irrigation", methods=["GET", "POST"])
def api_irrigation():
    """Get irrigation advice"""
    lang = session.get("language", "en")
    farm = get_farm()
    if not farm:
        return jsonify({"error": "Farm not set up"}), 400
    
    weather_data = get_weather(farm["location"])
    if request.method == "GET":
        return jsonify({"error": "Submit soil moisture to get watering advice."}), 400
    try:
        soil_moisture = float(request.form.get("soil_moisture", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid soil moisture value."}), 400
    if not 0 <= soil_moisture <= 100:
        return jsonify({"error": "Soil moisture must be between 0 and 100%."}), 400
    growth_stage = request.form.get("growth_stage", "vegetative")
    result = get_irrigation_advice(weather_data, soil_moisture, growth_stage, lang)
    result["priority"] = translate_text(result["priority"], lang)
    return jsonify(result)


@app.route("/api/maturity", methods=["GET", "POST"])
def api_maturity():
    """Estimate harvest from the farmer's submitted crop and field details."""
    if request.method == "GET":
        return jsonify({"error": "Enter crop and field details to estimate harvest."}), 400
    try:
        data = {
            "crop": request.form["crop"],
            "planting_date": request.form["planting_date"],
            "growth_stage": request.form["growth_stage"],
            "plant_height": float(request.form["plant_height"]),
            "branches": float(request.form["branches"]),
            "fruit_count": float(request.form["fruit_count"]),
            "fruit_size": float(request.form["fruit_size"]),
            "soil_moisture": float(request.form["soil_moisture"]),
            "temperature": float(request.form["temperature"]),
            "humidity": float(request.form["humidity"]),
            "rainfall": float(request.form["rainfall"]),
            "npk": request.form["npk"],
            "pest_severity": float(request.form["pest_severity"])
        }
        planting_date = date.fromisoformat(data["planting_date"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Complete all harvest fields with valid values."}), 400

    if planting_date > date.today():
        return jsonify({"error": "Planting date cannot be in the future."}), 400
    if data["growth_stage"] not in ("vegetative", "flowering", "fruiting", "maturity") or data["npk"] not in ("low", "medium", "adequate"):
        return jsonify({"error": "Select valid growth stage and NPK level."}), 400
    if not 0 <= data["soil_moisture"] <= 100 or not 0 <= data["humidity"] <= 100 or not 0 <= data["pest_severity"] <= 100:
        return jsonify({"error": "Moisture, humidity, and pest severity must be between 0 and 100."}), 400
    if min(data["plant_height"], data["branches"], data["fruit_count"], data["fruit_size"], data["rainfall"]) < 0:
        return jsonify({"error": "Plant, fruit, and rainfall values cannot be negative."}), 400
    result = estimate_harvest(data)
    lang = session.get("language", "en")
    result["crop"] = translate_text(result["crop"], lang)
    result["growth_stage"] = translate_text(result["growth_stage"], lang)
    result["estimate"] = translate_text(result["estimate"], lang)
    return jsonify(result)


@app.route("/api/ask", methods=["POST"])
def api_ask():
    """Ask a question using Gemini with full farm + location + weather context"""
    lang = session.get("language", "en")
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        if not os.environ.get("GEMINI_API_KEY"):
            return jsonify({"error": "Gemini API key not configured"})

        model = genai.GenerativeModel('gemini-2.5-flash')

        farm = get_farm()
        answer_language = LANGUAGES.get(lang, "English")

        # Build rich context with farm details and live weather
        farm_context = ""
        if farm:
            farm_context = (
                f"Farmer is growing {farm['crop']} in {farm['location']}. "
                f"Sowing date: {farm['sowing_date']}. "
                f"Soil type: {farm.get('soil_type', 'unknown')}. "
                f"Irrigation: {farm.get('irrigation', 'unknown')}. "
            )
            # Add live weather
            weather_data = get_weather(farm["location"])
            if weather_data and "current" in weather_data:
                cur = weather_data["current"]
                farm_context += (
                    f"Current weather at {farm['location']}: "
                    f"Temperature {cur.get('temp', '?')}°C, "
                    f"Humidity {cur.get('humidity', '?')}%, "
                    f"Rain probability {cur.get('rain_probability', '?')}%, "
                    f"Wind {cur.get('wind_speed', '?')} km/h. "
                )

        system_prompt = (
            f"You are FarmMitra, farming assistant. {farm_context}"
            f"Answer simply in {answer_language}. Format:\n\n"
            f"**Direct Answer**\n"
            f"1-2 sentences.\n\n"
            f"**What You Should Do**\n"
            f"- Action 1\n"
            f"- Action 2\n\n"
            f"**Important Note**\n"
            f"Short caution if needed.\n\n"
            f"Question: {question}"
        )

        response = model.generate_content(system_prompt)
        answer = response.text

        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/decision/<feature>")
def api_decision(feature):
    """Get explainable decision for a feature"""
    lang = session.get("language", "en")
    decision = decision_engine(feature, {}, lang)
    return jsonify(decision)


@app.route("/api/crop-recommend", methods=["GET", "POST"])
def api_crop_recommend():
    """Use Gemini AI to recommend crops based on farm location + live weather + soil + season"""
    lang = session.get("language", "en")
    farm = get_farm()
    if not farm:
        return jsonify({"error": "Farm not set up"}), 400

    try:
        answer_language = LANGUAGES.get(lang, "English")
        location = farm["location"]
        soil_type = farm.get("soil_type", "unknown")
        irrigation = farm.get("irrigation", "unknown")
        current_month = datetime.now().strftime("%B")

        # Get live weather for the farm location
        weather_data = get_weather(location)
        weather_context = ""
        if weather_data and "current" in weather_data:
            cur = weather_data["current"]
            weather_context = (
                f"Current weather: Temperature {cur.get('temp', '?')}°C, "
                f"Humidity {cur.get('humidity', '?')}%, "
                f"Rain probability {cur.get('rain_probability', '?')}%, "
                f"Wind {cur.get('wind_speed', '?')} km/h."
            )

        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = (
            f"Location: {location}. Month: {current_month}. Soil: {soil_type}. Irrigation: {irrigation}. {weather_context} "
            f"Recommend TOP 3 crops now. In {answer_language}. Format:\n"
            f"1. Crop name - Why (1-2 lines) - Yield - 2-3 tips\n"
            f"2. Crop name - Why (1-2 lines) - Yield - 2-3 tips\n"
            f"3. Crop name - Why (1-2 lines) - Yield - 2-3 tips\n"
        )
        response = model.generate_content(prompt)
        return jsonify({"recommendation": response.text, "location": location})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """Submit feedback on analysis"""
    data = request.get_json()
    analysis_id = data.get("analysis_id")
    helpful = data.get("helpful")
    comment = data.get("comment", "")
    
    if analysis_id is None or helpful is None:
        return jsonify({"error": "Missing required fields"}), 400
    
    with db() as conn:
        conn.execute(
            "INSERT INTO feedback(analysis_id, helpful, comment, created_at) VALUES(?,?,?,?)",
            (analysis_id, 1 if helpful else 0, comment, datetime.now().isoformat(timespec="seconds"))
        )
    
    return jsonify({"success": True})


@app.route("/api/reanalyze/<int:analysis_id>", methods=["POST"])
def api_reanalyze(analysis_id):
    """Re-analyze an existing image"""
    lang = session.get("language", "en")
    
    with db() as conn:
        analysis = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404
    
    image_path = analysis["image_path"]
    feature = analysis["feature"]
    
    prompts = {
        "leaf": "Analyze this plant leaf for diseases, pests, or abnormalities. Describe what you see and suggest treatments.",
        "health": "Assess the overall health of this crop. Describe growth stage, any issues, and general condition."
    }
    prompt = prompts.get(feature, "Analyze this agricultural image.")
    
    result = analyze_with_gemini(image_path, prompt, lang)
    
    if "error" not in result:
        with db() as conn:
            conn.execute(
                "UPDATE analyses SET result = ?, confidence = ?, created_at = ? WHERE id = ?",
                (result["result"], result.get("confidence", 0), datetime.now().isoformat(timespec="seconds"), analysis_id)
            )
    
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
