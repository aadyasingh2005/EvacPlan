"use client"
import { useRef, useState, useEffect } from "react"
import { FeatureGroup, Marker, Polyline, useMapEvents, Circle, Popup, LayerGroup } from "react-leaflet"
import { EditControl } from "react-leaflet-draw"
import L, { type LatLngExpression } from "leaflet"
import { useMode } from "../context/mode-context"
import { toast } from "sonner"
import "../styles/MapView.css"

// Custom marker icons
const startIcon = L.divIcon({
  className: "custom-marker-icon",
  html: `<div class="marker-pin start-pin">
           <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" class="lucide lucide-map-pin">
             <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path>
             <circle cx="12" cy="10" r="3"></circle>
           </svg>
         </div>`,
  iconSize: [40, 40],
  iconAnchor: [20, 40],
  popupAnchor: [0, -35],
})

const endIcon = L.divIcon({
  className: "custom-marker-icon",
  html: `<div class="marker-pin end-pin">
           <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" class="lucide lucide-navigation">
             <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
           </svg>
         </div>`,
  iconSize: [40, 40],
  iconAnchor: [20, 40],
  popupAnchor: [0, -35],
})

// Agent icon
const agentIcon = L.divIcon({
  className: "agent-icon",
  html: `<div class="agent-dot"></div>`,
  iconSize: [10, 10],
  iconAnchor: [5, 5],
})

function sampleRoutePoints(routeCoords: [number, number][], interval = 5): [number, number][] {
  if (!routeCoords || routeCoords.length === 0) return []
  const sampled: [number, number][] = []
  for (let i = 0; i < routeCoords.length; i += interval) {
    const [lng, lat] = routeCoords[i]
    sampled.push([lat, lng])
  }
  if (sampled.length === 0 || sampled[0][0] !== routeCoords[0][1] || sampled[0][1] !== routeCoords[0][0]) {
    sampled.unshift([routeCoords[0][1], routeCoords[0][0]])
  }
  if (
    sampled[sampled.length - 1][0] !== routeCoords[routeCoords.length - 1][1] ||
    sampled[sampled.length - 1][1] !== routeCoords[routeCoords.length - 1][0]
  ) {
    sampled.push([routeCoords[routeCoords.length - 1][1], routeCoords[routeCoords.length - 1][0]])
  }
  return sampled
}

// Calculate crowd density score (used to determine number of agents)
function calculateCrowdDensity(point) {
  if (!point) return 5; // Default value if no data
  
  // Use currentSpeed as inverse indicator of crowd density
  // Lower speed = higher density
  if (point.currentSpeed === null) return 5;
  
  // Convert speed to density score (higher density at lower speeds)
  if (point.currentSpeed < 10) {
    return Math.floor(Math.random() * 5) + 15; // Heavy crowd: 15-20 agents
  } else if (point.currentSpeed < 20) {
    return Math.floor(Math.random() * 5) + 8;  // Medium crowd: 8-12 agents
  } else {
    return Math.floor(Math.random() * 3) + 3;  // Light crowd: 3-5 agents
  }
}

const MapView = ({ routeData, blockages, setBlockages, startPoint, endPoint, setStartPoint, setEndPoint, mapRef }) => {
  const drawnItemsRef = useRef<L.FeatureGroup>(null)
  const [densityPoints, setDensityPoints] = useState<any[]>([])
  const { mode, markerMode, setMarkerMode, isDrawingObstacle } = useMode()
  const [routeAnimation, setRouteAnimation] = useState(0)
  
  // Agent animation states
  const [agents, setAgents] = useState([])
  const [isAnimating, setIsAnimating] = useState(false)
  const animationRef = useRef(null)
  const routePointsRef = useRef([])
  const [routeDuration, setRouteDuration] = useState(0)
  const [routeDistance, setRouteDistance] = useState(0)

  // Handle map clicks based on current marker mode
  const map = useMapEvents({
    click(e) {
      if (markerMode === "none" || isDrawingObstacle) return

      const latlng: [number, number] = [e.latlng.lat, e.latlng.lng]
      if (markerMode === "start") {
        setStartPoint(latlng)
        toast.success("Start Point Set", {
          description: `Start point set at latitude ${latlng[0].toFixed(5)}, longitude ${latlng[1].toFixed(5)}`,
        })
      } else if (markerMode === "end") {
        setEndPoint(latlng)
        toast.success("End Point Set", {
          description: `Destination set at latitude ${latlng[0].toFixed(5)}, longitude ${latlng[1].toFixed(5)}`,
        })
      }
      setMarkerMode("none")
    },
  })

  // Handle drawing creation
  const handleDrawCreated = (e: any) => {
    const layer = e.layer
    let coords: [number, number][] = []
    if (layer instanceof L.Polygon || layer instanceof L.Rectangle) {
      const latLngs = (layer.getLatLngs()[0] as L.LatLng[]).map(
        (latlng) => [latlng.lat, latlng.lng] as [number, number],
      )
      if (
        latLngs.length > 0 &&
        (latLngs[0][0] !== latLngs[latLngs.length - 1][0] || latLngs[0][1] !== latLngs[latLngs.length - 1][1])
      ) {
        latLngs.push(latLngs[0])
      }
      coords = latLngs
      setBlockages([...blockages, { type: layer instanceof L.Polygon ? "polygon" : "rectangle", coords }])
      toast.success("Obstacle Added", {
        description: "A new obstacle has been added to the map.",
      })
    }
  }

  const handleDrawDeleted = (e: any) => {
    setBlockages([])
    toast.info("Obstacles Cleared", {
      description: "All obstacles have been removed from the map.",
    })
  }

  const toLatLngs = (coords: [number, number][]) => coords.map(([lat, lng]) => [lat, lng] as LatLngExpression)

  const getRouteLatLngs = () => {
    if (!routeData || !routeData.features || !routeData.features[0]) return []
    return routeData.features[0].geometry.coordinates.map(
      ([lng, lat]: [number, number]) => [lat, lng] as LatLngExpression,
    )
  }

  // Extract route information
  useEffect(() => {
    if (routeData && routeData.features && routeData.features[0]) {
      const properties = routeData.features[0].properties;
      const summary = properties.summary || {};
      setRouteDuration(summary.duration || 0);
      setRouteDistance(summary.distance || 0);
      console.log(`Route properties loaded: Duration ${summary.duration}s, Distance ${summary.distance}m`);
    }
  }, [routeData]);

  // Function to initialize agents based on crowd density
  const initializeAgents = (startLocationDensity = null) => {
    // Get full route points for animation
    const routePoints = getRouteLatLngs()
    routePointsRef.current = routePoints
    
    if (routePoints.length < 2) return
    
    // Determine agent count based on crowd density at starting location
    let agentCount = 5; // Default value
    
    if (startLocationDensity) {
      // Use the crowd density of the first point (starting location)
      agentCount = calculateCrowdDensity(startLocationDensity);
    }
    
    console.log(`Initializing ${agentCount} agents based on starting location density`);
    
    // Calculate agent speed based on route duration and distance
    let baseSpeed = 0.2; // Default speed
    
    if (routeDuration > 0 && routeDistance > 0) {
      // Calculate a speed that would complete the route in approximately the same time
      // as the calculated route duration
      const routeLength = routePoints.length;
      // Convert duration from seconds to animation frames (60fps approximation)
      const durationInFrames = routeDuration * 0.05; // Adjust multiplier for visualization speed
      
      // Speed = total segments to travel / frames to complete
      baseSpeed = routeLength / durationInFrames;
      
      // Ensure speed is within a reasonable range for visualization
      baseSpeed = Math.max(0.05, Math.min(baseSpeed, 0.8));
      
      console.log(`Calculated base agent speed: ${baseSpeed} based on route duration: ${routeDuration}s`);
    }
    
    // Create initial agents with calculated speed
    const newAgents = Array(agentCount).fill(0).map((_, i) => ({
      id: `agent-${i}`,
      position: routePoints[0],
      progress: Math.random() * 5, // Stagger initial positions slightly
      speed: baseSpeed * (0.8 + Math.random() * 0.4), // Add small random variation to base speed
      color: ["#3388ff", "#ff3300", "#33cc33", "#ffcc00", "#cc33ff"][i % 5],
    }))
    
    setAgents(newAgents)
    return newAgents
  }

  // Animation function to move agents along route
  const animateAgents = (timestamp) => {
    const routePoints = routePointsRef.current
    
    if (!isAnimating || routePoints.length < 2) {
      animationRef.current = null
      return
    }
    
    setAgents(currentAgents => {
      return currentAgents.map(agent => {
        // Update agent progress along route
        let newProgress = agent.progress + agent.speed
        
        // Calculate position on the route
        const segmentIndex = Math.floor(newProgress)
        const segmentProgress = newProgress - segmentIndex
        
        // Reset if reached end of route
        if (segmentIndex >= routePoints.length - 1) {
          newProgress = 0
          return {
            ...agent,
            position: routePoints[0],
            progress: newProgress
          }
        }
        
        // Interpolate position between route points
        const currentPoint = routePoints[segmentIndex]
        const nextPoint = routePoints[segmentIndex + 1]
        
        const position = [
          currentPoint[0] + (nextPoint[0] - currentPoint[0]) * segmentProgress,
          currentPoint[1] + (nextPoint[1] - currentPoint[1]) * segmentProgress
        ]
        
        return {
          ...agent,
          position,
          progress: newProgress
        }
      })
    })
    
    animationRef.current = requestAnimationFrame(animateAgents)
  }

  // Start/stop animation
  useEffect(() => {
    if (routeData && routeData.features && routeData.features[0] && mode === "crowd") {
      // Wait for density data to be available before initializing agents
      if (densityPoints.length > 0) {
        // Use the first density point (starting location) to determine agent count
        const startLocationDensity = densityPoints[0];
        const initialAgents = initializeAgents(startLocationDensity);
        if (initialAgents) {
          setIsAnimating(true);
        }
      } else {
        // If no density data yet, initialize with default values
        const initialAgents = initializeAgents();
        if (initialAgents) {
          setIsAnimating(true);
        }
      }
    } else {
      setIsAnimating(false);
      setAgents([]);
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [routeData, mode, densityPoints]);
  
  // Handle animation frame
  useEffect(() => {
    if (isAnimating && agents.length > 0 && !animationRef.current) {
      animationRef.current = requestAnimationFrame(animateAgents)
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
    }
  }, [isAnimating, agents])

  // Fetch traffic density data when route changes
  useEffect(() => {
    const fetchDensity = async () => {
      if (routeData && routeData.features && routeData.features[0]) {
        const coords = routeData.features[0].geometry.coordinates
        const sampledPoints = sampleRoutePoints(coords, 7)
        try {
          // Attempt to fetch real data from the API
          const response = await fetch('/api/traffic/density', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ points: sampledPoints }),
          });
          
          if (response.ok) {
            const densityData = await response.json();
            setDensityPoints(densityData);
            setRouteAnimation((prev) => prev + 1);
          } else {
            console.warn("API response not OK, using mock data instead");
            // Use mock data as fallback
            const mockDensity = sampledPoints.map(([lat, lng]) => ({
              lat,
              lon: lng,
              currentSpeed: Math.random() * 30,
              freeFlowSpeed: Math.random() * 50 + 20,
              confidence: Math.random().toFixed(2),
            }))
            setDensityPoints(mockDensity)
            setRouteAnimation((prev) => prev + 1)
          }
        } catch (e) {
          console.error("Error fetching density data:", e)
          // Use mock data as fallback
          const mockDensity = sampledPoints.map(([lat, lng]) => ({
            lat,
            lon: lng,
            currentSpeed: Math.random() * 30,
            freeFlowSpeed: Math.random() * 50 + 20,
            confidence: Math.random().toFixed(2),
          }))
          setDensityPoints(mockDensity)
          setRouteAnimation((prev) => prev + 1)
        }
      } else {
        setDensityPoints([])
      }
    }
    fetchDensity()
  }, [routeData])

  // Render different map elements based on current mode
  const renderModeSpecificElements = () => {
    switch (mode) {
      case "heatmap":
        return (
          <LayerGroup>
            {densityPoints.map((pt, idx) => (
              <Circle
                key={idx}
                center={[pt.lat, pt.lon]}
                radius={200}
                pathOptions={{
                  color: "transparent",
                  fillColor:
                    pt.currentSpeed === null
                      ? "#555555"
                      : pt.currentSpeed < 10
                        ? "#ff0000"
                        : pt.currentSpeed < 20
                          ? "#ff9900"
                          : "#00ff00",
                  fillOpacity: 0.7,
                }}
              >
                <Popup>
                  <div className="text-black">
                    <b>Current Speed:</b> {pt.currentSpeed ?? "N/A"} km/h
                    <br />
                    <b>Free Flow Speed:</b> {pt.freeFlowSpeed ?? "N/A"} km/h
                    <br />
                    <b>Confidence:</b> {pt.confidence ?? "N/A"}
                    <br />
                    <b>Estimated Crowd:</b> {calculateCrowdDensity(pt)} people
                  </div>
                </Popup>
              </Circle>
            ))}
          </LayerGroup>
        )
      case "defense":
        return (
          <LayerGroup>
            {blockages.map((blockage, idx) => (
              <Circle
                key={`defense-${idx}`}
                center={blockage.coords[0]}
                radius={300}
                pathOptions={{
                  color: "#ff3300",
                  fillColor: "#ff3300",
                  fillOpacity: 0.3,
                  dashArray: "5, 10",
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="text-black">
                    <b>Defense Zone {idx + 1}</b>
                    <br />
                    Radius: 300m
                    <br />
                    Status: Active
                  </div>
                </Popup>
              </Circle>
            ))}
          </LayerGroup>
        )
      case "crowd":
        // No heatmap elements shown in crowd mode - only agents will be shown
        return null
      default: // evacuate mode
        return null
    }
  }

  return (
    <>
      {isDrawingObstacle && (
        <FeatureGroup ref={drawnItemsRef as any}>
          <EditControl
            position="topright"
            onCreated={handleDrawCreated}
            onDeleted={handleDrawDeleted}
            draw={{
              polyline: false,
              circle: true,
              marker: false,
              circlemarker: false,
              polygon: { shapeOptions: { color: "#ff3300", fillOpacity: 0.3 } },
              rectangle: { shapeOptions: { color: "#ff3300", fillOpacity: 0.3 } },
            }}
          />
        </FeatureGroup>
      )}

      {startPoint && (
        <Marker
          position={startPoint}
          icon={startIcon}
          eventHandlers={{
            click: () => {
              map.setView(startPoint, map.getZoom())
            },
          }}
        >
          <Popup>
            <div className="text-black">
              <b>Starting Point</b>
              <br />
              Lat: {startPoint[0].toFixed(5)}
              <br />
              Lng: {startPoint[1].toFixed(5)}
              {densityPoints.length > 0 && (
                <>
                  <br />
                  <b>Crowd Density:</b> {calculateCrowdDensity(densityPoints[0])} people
                </>
              )}
            </div>
          </Popup>
        </Marker>
      )}

      {endPoint && (
        <Marker
          position={endPoint}
          icon={endIcon}
          eventHandlers={{
            click: () => {
              map.setView(endPoint, map.getZoom())
            },
          }}
        >
          <Popup>
            <div className="text-black">
              <b>Destination</b>
              <br />
              Lat: {endPoint[0].toFixed(5)}
              <br />
              Lng: {endPoint[1].toFixed(5)}
              {routeDuration > 0 && (
                <>
                  <br />
                  <b>Trip Duration:</b> {Math.floor(routeDuration / 60)} min {Math.round(routeDuration % 60)} sec
                  <br />
                  <b>Distance:</b> {(routeDistance / 1000).toFixed(2)} km
                </>
              )}
            </div>
          </Popup>
        </Marker>
      )}

      {routeData && routeAnimation > 0 && (
        <Polyline
          positions={getRouteLatLngs()}
          pathOptions={{
            color:
              mode === "evacuate"
                ? "#0088ff"
                : mode === "defense"
                  ? "#ff5500"
                  : mode === "heatmap"
                    ? "#ffcc00"
                    : "#00ccff",
            weight: 5,
            opacity: 0.8,
            lineCap: "round",
            lineJoin: "round",
            dashArray: mode === "defense" ? "10, 10" : undefined,
          }}
          className="route-path"
        />
      )}

      {/* Render animated agents */}
      {agents.map(agent => (
        <Marker
          key={agent.id}
          position={agent.position}
          icon={L.divIcon({
            className: "agent-icon",
            html: `<div class="agent-dot" style="background-color: ${agent.color}"></div>`,
            iconSize: [10, 10],
            iconAnchor: [5, 5],
          })}
        >
          <Popup>
            <div className="text-black">
              <b>Agent {agent.id}</b>
              <br />
              Speed: {(agent.speed * 30).toFixed(1)} km/h
            </div>
          </Popup>
        </Marker>
      ))}

      {renderModeSpecificElements()}

      {blockages.map((blockage, idx) => (
        <Polyline
          key={`blockage-${idx}`}
          positions={toLatLngs(blockage.coords)}
          pathOptions={{
            color: "#ff3300",
            fillColor: "#ff3300",
            fillOpacity: 0.3,
            weight: 3,
          }}
        />
      ))}
    </>
  )
}

export default MapView