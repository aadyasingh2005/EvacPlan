# Evacuation Route Planner Using Real-Time Crowd Simulation
This project is a disaster management web application that helps plan optimal evacuation routes using real-time crowd simulation and user-inputted road conditions. Users—either officials or civilians—can mark blocked or inaccessible roads on an interactive map. The simulation engine dynamically updates and computes alternate escape paths based on this evolving input.

# Features

🗺️ Interactive Map: Built with Leaflet.js, allows users to view roads, blocked areas, and evacuation paths.

🧠 Real-Time Crowd Simulation: Simulates crowd flow based on road closures and congestion logic.

📡 Twilio WhatsApp Bot: Citizens can report blocked roads or receive route updates through WhatsApp integration.

🌐 Two External APIs:

  OpenRouteService (ORS) API: For dynamic route planning.

  TomTom API: For visualizing real-time heatmaps indicating crowd density.

⚡ FastAPI Backend: Handles user inputs, processes simulation requests, and interacts with APIs.


# Tech Stack

Frontend: React, Leaflet.js

Backend: Python (FastAPI)

Communication: Twilio API for WhatsApp bot

Routing & Maps: OpenRouteService API, TomTom API

# Setup Instructions
1)Clone the repository

2)Install dependencies

    pip install fastapi uvicorn

    npm install leaflet

3)Start the backend

    uvicorn main:app --reload  

4) Open the frontend in your browser.
