"use client";

import { useState } from "react";
import { createUserWithEmailAndPassword } from "firebase/auth";
import { auth, db } from "../../lib/firebase";
import { doc, setDoc } from "firebase/firestore";
import { useRouter } from "next/navigation";
import "../auth.css";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const handleSignup = async () => {
    const userCred = await createUserWithEmailAndPassword(auth, email, password);

    await setDoc(doc(db, "users", userCred.user.uid), {
      email,
      createdAt: new Date()
    });

    router.push("/dashboard");
  };

  return (
    <div className="auth-wrapper">

      {/* LEFT */}
      <div className="auth-left">

        <div className="back" onClick={() => router.push("/")}>
          ← Back to Home
        </div>

        <h1>Create Account</h1>
        <p>Start using MedMitra today</p>

        <input placeholder="Email" onChange={(e) => setEmail(e.target.value)} />
        <input type="password" placeholder="Password" onChange={(e) => setPassword(e.target.value)} />

        <button onClick={handleSignup}>Sign Up</button>

        <div className="divider">or continue with</div>

        <div className="socials">
          <div>G</div>
          <div>A</div>
          <div>F</div>
        </div>

        <p className="bottom-text">
          Already have an account?{" "}
          <span onClick={() => router.push("/login")}>Login</span>
        </p>

      </div>

      {/* RIGHT */}
      <div className="auth-right">
        <img src="/robot.png" alt="AI assistant" className="hero-img" />

        <h2>MedMitra</h2>
        <p>Smart AI-powered healthcare assistant</p>
      </div>

    </div>
  );
}