"use client";

import { useState } from "react";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../../lib/firebase";
import { useRouter } from "next/navigation";
import "../auth.css";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const handleLogin = async () => {
    await signInWithEmailAndPassword(auth, email, password);
    router.push("/dashboard");
  };

  return (
    <div className="auth-wrapper">

      {/* LEFT */}
      <div className="auth-left">

        <div className="back" onClick={() => router.push("/")}>
          ← Back to Home
        </div>

        <h1>Welcome back!</h1>
        <p>Login to continue using MedMitra</p>

        <input placeholder="Email" onChange={(e) => setEmail(e.target.value)} />
        <input type="password" placeholder="Password" onChange={(e) => setPassword(e.target.value)} />

        <button onClick={handleLogin}>Login</button>

        <div className="divider">or continue with</div>

        <div className="socials">
          <div>G</div>
          <div>A</div>
          <div>F</div>
        </div>

        <p className="bottom-text">
          Not a member?{" "}
          <span onClick={() => router.push("/signup")}>Register now</span>
        </p>

      </div>

      {/* RIGHT */}
      <div className="auth-right">
        <img src="/robot.png" alt="AI assistant" className="hero-img" />

        <h2>Smart Prescription Analysis</h2>
        <p>Analyze medicines, detect risks, stay safe.</p>
      </div>

    </div>
  );
}