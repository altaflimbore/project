import streamlit as st
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
import speech_recognition as sr
import warnings

# Function to load data and preprocess
def load_data(file_path):
    data = pd.read_csv(file_path)
    if 'Unnamed: 133' in data.columns:
        data = data.drop('Unnamed: 133', axis=1)
    return data

# Load the datasets
training_data = load_data("disease dataset/Training.csv")
testing_data = load_data("disease dataset/Testing.csv")

# Preprocess data
X_train = training_data.drop('prognosis', axis=1)
y_train = training_data['prognosis']

# Create a pipeline for preprocessing and modeling
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),  # Impute missing values with mean
#    ('classifier', LogisticRegression(multi_class='multinomial', max_iter=1000))
    ('classifier', LogisticRegression())
])

# Train the model using the pipeline
pipeline.fit(X_train, y_train)

# Prescription dictionary mapping diseases to drugs
prescription_dict = {
    'Fungal infection': 'Drug_A',
    'Allergy': 'Drug_B',
    'GERD': 'Drug_C',
    'Chronic cholestasis': 'Drug_D',
    'Drug Reaction': 'Drug_E',
    'Acne': 'Dolo 650',
    # Add more mappings as per your dataset
}

# Function to predict disease and generate prescription
def predict_disease(symptoms):
    # Predict disease
    disease_prediction = pipeline.predict([symptoms])[0]
    
    # Get prescription for predicted disease
    prescription = prescription_dict.get(disease_prediction, "No prescription found")
    
    return disease_prediction, prescription

# Function to handle voice input using SpeechRecognition
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Speak your symptoms.")
        audio = recognizer.listen(source)
    
    try:
        text = recognizer.recognize_google(audio)
        st.success(f"Recognized text: {text}")
        return text
    except sr.UnknownValueError:
        st.warning("Sorry, I could not understand your voice.")
        return None
    except sr.RequestError:
        st.error("Speech recognition service is currently unavailable.")
        return None

# Main function to run Streamlit app
def main():
    st.title("Disease Prognosis Prediction and Prescription Generator")
    st.markdown("[Go Back](http://localhost:8000)")
    #st.markdown(title, unsafe_allow_html=True)
    # Adding CSS styling
    # Set the background image

    #st.set_page_config(page_title="Page Title", layout="wide")

    st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)
    background_image = """
       <style>
       [data-testid="stAppViewContainer"] > .main {
       background: url('https://t4.ftcdn.net/jpg/06/32/90/79/360_F_632907942_M6CVHD1ivhUrWK1X49PkBlSH3ooNPsog.jpg');
       background-size: 100vw 100vh;  # This sets the size to cover 100% of the viewport width and height
       background-position: center;  
       background-repeat: no-repeat;
       }
       </style>
       """

    st.markdown(background_image, unsafe_allow_html=True)
    styling =  """
        <style>
        body {
            background-color: DodgerBlue;
            background: url('https://images.ctfassets.net/hrltx12pl8hq/01rJn4TormMsGQs1ZRIpzX/16a1cae2440420d0fd0a7a9a006f2dcb/Artboard_Copy_231.jpg?fit=fill&w=600&h=600'); 
        }
        .stButton button {
            background-color: navy;
            color: white;
        }
        .stButton button:hover {
            background-color: white;
        }
        .stCheckbox label {
            font-size: 18px;
        }
        .stSidebar {
            background-color: DodgerBlue;
        }
        .stSidebar h2 {
            color: #4CAF50;
        }
        .stSidebar .stRadio label {
            font-size: 16px;
            color: #4CAF50;
        }
        .stMarkdown h2, .stMarkdown h3 {
            color: #4CAF50;
        }
        .stInfo, .stSuccess, .stWarning, .stError {
            border-radius: 10px;
            padding: 10px;
        }
        </style>
        """
    st.markdown(styling, unsafe_allow_html=True)

    # Sidebar for user input methods
    input_method = st.sidebar.radio("Select Input Method", ("Manual selection", "Voice prompts"))

    # Manual selection of symptoms
    if input_method == "Manual selection":
        st.subheader("Select Symptoms")
        selected_symptoms = []
        for symptom in X_train.columns:
            selected = st.checkbox(symptom)
            if selected:
                selected_symptoms.append(1)  # Assuming 1 represents presence of symptom
            else:
                selected_symptoms.append(0)  # 0 represents absence of symptom

        # Predict disease based on selected symptoms
        if st.button("Predict"):
            if any(selected_symptoms):
                disease_prediction, prescription = predict_disease(selected_symptoms)
                st.subheader("Prediction")
                st.write(f"The predicted disease is: {disease_prediction}")
                st.subheader("Prescription")
                st.write(f"Prescribed drug: {prescription}")
            else:
                st.warning("Please select at least one symptom to predict the disease.")
    
    # Voice prompts
    elif input_method == "Voice prompts":
        st.subheader("Voice Input")
        symptoms_text = get_voice_input()
        if symptoms_text:
            # Process text to determine selected symptoms
            selected_symptoms = [1 if symptom.lower() in symptoms_text.lower() else 0 for symptom in X_train.columns]
            
            # Predict disease based on selected symptoms
            disease_prediction, prescription = predict_disease(selected_symptoms)
            st.subheader("Prediction")
            st.write(f"The predicted disease is: {disease_prediction}")
            st.subheader("Prescription")
            st.write(f"Prescribed drug: {prescription}")

# Run the main function to start the Streamlit app
if __name__ == "__main__":
    main()
