"use client";

import { auth } from "../../lib/firebase";
import { signOut } from "firebase/auth";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const router = useRouter();

  const handleLogout = async () => {
    await signOut(auth);
    router.push("/login");
  };

  return (
    <div style={{ padding: "40px" }}>
      <h2>Dashboard</h2>

      <p>Welcome: {auth.currentUser?.email}</p>

      <button onClick={handleLogout}>Logout</button>

      <p style={{ marginTop: "20px", color: "red" }}>
        As MedMitra states, consult a doctor. We only provide suggestions.
      </p>
    </div>
  );
}
