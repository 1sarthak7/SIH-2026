import React from "react";

const Globe: React.FC = () => {
  return (
    <>
      <style>
        {`
          @keyframes earthRotate {
            0% { background-position: 0 0; }
            100% { background-position: 400px 0; }
          }
          @keyframes twinkling { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
          @keyframes twinkling-slow { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
          @keyframes twinkling-long { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
          @keyframes twinkling-fast { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
        `}
      </style>
      <div className="flex items-center justify-center">
        <div
          className="relative rounded-full overflow-hidden"
          style={{
            width: "clamp(220px, 24vw, 320px)",
            height: "clamp(220px, 24vw, 320px)",
            backgroundImage: "url('https://cdn.21st.dev/assets/mirror/f2/f2fe23d0c6a8406962e4c5ef969e13dc9de3faf37d3e7258a1067173325b254f.jpg')",
            backgroundSize: "cover",
            backgroundPosition: "left",
            animation: "earthRotate 30s linear infinite",
            boxShadow: "0 0 20px rgba(255,255,255,0.2), -5px 0 8px #c3f4ff inset, 15px 2px 25px #000 inset, -24px -2px 34px rgba(195,244,255,0.6) inset, 250px 0 44px rgba(0,0,0,0.4) inset, 150px 0 38px rgba(0,0,0,0.67) inset",
          }}
        >
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "-20px", animation: "twinkling 3s infinite" }}
          />
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "-40px", top: "30px", animation: "twinkling-slow 2s infinite" }}
          />
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "350px", top: "90px", animation: "twinkling-long 4s infinite" }}
          />
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "200px", top: "290px", animation: "twinkling 3s infinite" }}
          />
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "50px", top: "270px", animation: "twinkling-fast 1.5s infinite" }}
          />
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "250px", top: "-50px", animation: "twinkling-long 4s infinite" }}
          />
          <div
            className="absolute w-1 h-1 bg-white rounded-full"
            style={{ left: "290px", top: "60px", animation: "twinkling-slow 2s infinite" }}
          />
        </div>
      </div>
    </>
  );
};

export default Globe;
