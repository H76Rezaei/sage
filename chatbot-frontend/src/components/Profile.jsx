import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Profile.css";

const Profile = () => {
  const navigate = useNavigate();
  const token = localStorage.getItem("access_token");

  const [profileData, setProfileData] = useState({
    first_name: "",
    last_name: "",
    phone_number: "",
    email: "",
    birth_date: "",
  });
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetch("http://localhost:8000/user/profile", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch profile");
        }
        const data = await response.json();
        setProfileData(data);
        setLoading(false);
      } catch (error) {
        setErrorMsg("Error fetching profile");
        setLoading(false);
      }
    };
    fetchProfile();
  }, [token]);

  const handleChange = (e) => {
    setProfileData({
      ...profileData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    try {
      const response = await fetch("http://localhost:8000/user/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          first_name: profileData.first_name,
          last_name: profileData.last_name,
          phone_number: profileData.phone_number,
          birth_date: profileData.birth_date,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update profile");
      }
      const updatedData = await response.json();
      setSuccessMsg("Profile updated successfully");
      setProfileData(updatedData);
    } catch (error) {
      setErrorMsg(error.message);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="profile-container">
      <h2>Your Profile</h2>
      {errorMsg && <div className="error">{errorMsg}</div>}
      {successMsg && <div className="success">{successMsg}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>First Name</label>
          <input
            type="text"
            name="first_name"
            value={profileData.first_name}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Last Name</label>
          <input
            type="text"
            name="last_name"
            value={profileData.last_name}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Phone Number</label>
          <input
            type="text"
            name="phone_number"
            value={profileData.phone_number}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label>Email (Not editable)</label>
          <input type="email" name="email" value={profileData.email} disabled />
        </div>
        <div className="form-group">
          <label>Birth Date</label>
          <input
            type="date"
            name="birth_date"
            value={profileData.birth_date}
            onChange={handleChange}
          />
        </div>
        <button type="submit" className="update-button">
          Update Profile
        </button>
      </form>
    </div>
  );
};

export default Profile;
