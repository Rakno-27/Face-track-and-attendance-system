# FaceTrack
**An Intelligent Biometric Attendance & Timetable Management Dashboard**

FaceTrack is a high-performance, real-time facial recognition attendance system heavily integrated with a dynamic daily academic timetable. Designed with a pure Python backend utilizing `dlib` and `OpenCV`, it automates student attendance tracking without requiring database clusters or external network processors. 

## Features
* **Real-time Live Scanning**: Tap into native webcams to identify students continuously tracking against attendance margins seamlessly.
* **Timetable-driven Constraints**: Automatically registers subjects and lecture types based on a predefined daily timeframe logic (Open only 15 minutes before the start time). 
* **Dynamic Custom Overrides**: Need to schedule a makeup exam on a Sunday? The admin panel allows you to seamlessly override the core timetable schedules with interactive Custom Sessions bounding without rewriting codebase timetables.
* **Local Biometric Architecture**: Enrolls students directly from capturing their portraits. Biometric matrices are locally pickled optimizing retrieval avoiding expensive database fetches.
* **CSV Export**: Fully featured dashboard provides immediate metric extraction of specific subjects and standard `.csv` export functionality globally.
* **Manual Capture Capability**: If a native camera stream isn't viable, administrators can safely capture static snapshots verifying attendance synchronously.

## Technology Stack
- **Framework**: Flask (Python 3.0) 
- **Computer Vision**: OpenCV (`cv2`) 
- **Biometric Analysis**: `face_recognition` (wrapping `dlib` C++ Engine)
- **Frontend**: Pure Vanilla JS / CSS / HTML 
- **Data Persistence**: JSON (`students.json`, `attendance.json`) & Pickle arrays (`encodings.pkl`). 

## Installation Guide

To run FaceTrack on your local machine or server securely, follow the process below:

### 1. Prerequisites 
Ensure you have **Python 3.9+** and a C++ compiler installed (essential natively for compiling `dlib` modules).

### 2. Environment Setup
Create an isolated python environment to encapsulate requirements:
```bash
python -m venv venv
```
Activate the environment:
* **Windows**: `venv\Scripts\activate`
* **Mac/Linux**: `source venv/bin/activate`

### 3. Install Dependencies
Install all required biometric and structural frameworks utilizing the package manager:
```bash
pip install -r requirements.txt
```

### 4. Running the Dashboard
Initialize the Flask service binding on your local loopback. 
```bash
python app.py
```
Open your favourite browser and navigate to exactly: **`http://127.0.0.1:5000`**

### Security & Data Deletion
We implemented an **Administrative Dashboard** specifically for tracking biometric parameters. Open the Settings Gear icon inside the bottom-left sidebar navigation. Here you can efficiently invoke memory scrubs, rebuild timetable components, drop attendance logs locally, or forcibly eject massive compiled `.pkl` biometric matrices maintaining compliance with local regulations natively.
