import "./Profile.css";
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

function Profile() {
  const navigate = useNavigate();

  const [userData, setUserData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    phoneNumber: "",
    birthDate: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUserData = async () => {
      const token = localStorage.getItem("token");

      if (!token) {
        navigate("/login");
        return;
      }

      try {
        const response = await fetch("http://127.0.0.1:8000/profile", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setUserData(data);
        } else {
          setError("Failed to fetch user data.");
        }
      } catch (error) {
        console.error("Error:", error);
        setError("An error occurred while fetching user data.");
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, [navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setUserData({ ...userData, [name]: value });
  };

  const handleUpdate = async (e) => {
    e.preventDefault();

    const token = localStorage.getItem("token");

    if (!token) {
      navigate("/login");
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/profile/update", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(userData),
      });

      if (response.ok) {
        alert("Profile updated successfully!");
      } else {
        alert("Failed to update profile.");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("An error occurred while updating your profile.");
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  if (loading) {
    return <div className="auth-container">Loading...</div>;
  }

  if (error) {
    return <div className="auth-container">Error: {error}</div>;
  }

  return (
    <div className="auth-container">
      <h2>Profile</h2>
      <form className="auth-form" onSubmit={handleUpdate}>
        <input
          type="text"
          name="firstName"
          placeholder="First Name"
          value={userData.firstName}
          onChange={handleChange}
          required
        />
        <input
          type="text"
          name="lastName"
          placeholder="Last Name"
          value={userData.lastName}
          onChange={handleChange}
          required
        />
        <input
          type="email"
          name="email"
          placeholder="Email"
          value={userData.email}
          disabled
        />
        <input
          type="text"
          name="phoneNumber"
          placeholder="Phone Number"
          value={userData.phoneNumber}
          onChange={handleChange}
          required
        />
        <input
          type="date"
          name="birthDate"
          value={userData.birthDate}
          onChange={handleChange}
          required
        />
        <button type="submit">Update Profile</button>
      </form>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}

export default Profile;
