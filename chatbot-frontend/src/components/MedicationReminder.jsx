import React, { useState, useEffect } from "react";
import "./MedicationReminder.css";

const MedicationReminder = () => {
  const [medications, setMedications] = useState([]);
  const [medicationName, setMedicationName] = useState("");
  const [medicationTime, setMedicationTime] = useState("");
  const [repeatEvery, setRepeatEvery] = useState(1);
  const [isReminderActive, setIsReminderActive] = useState(false);

  useEffect(() => {
    const savedMedications = localStorage.getItem("medications");
    if (savedMedications) {
      setMedications(JSON.parse(savedMedications));
    }
  }, []);

  const saveToLocalStorage = (medications) => {
    localStorage.setItem("medications", JSON.stringify(medications));
  };

  const addMedication = () => {
    if (medicationName && medicationTime && repeatEvery) {
      const newMedication = {
        name: medicationName,
        time: medicationTime,
        repeatEvery,
      };
      const updatedMedications = [...medications, newMedication];
      setMedications(updatedMedications);
      saveToLocalStorage(updatedMedications);
      setMedicationName("");
      setMedicationTime("");
      setRepeatEvery(1);
    }
  };

  const deleteMedication = (index) => {
    const updatedMedications = medications.filter((_, i) => i !== index);
    setMedications(updatedMedications);
    saveToLocalStorage(updatedMedications);
  };

  const checkForReminders = () => {
    const currentTime = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    medications.forEach((medication) => {
      if (medication.time === currentTime && !isReminderActive) {
        alert(`It's time to take your medication: ${medication.name}`);
        setIsReminderActive(true);
      }
    });
  };

  return (
    <div className="medication-reminder-container">
      <h1 className="header-title">Medication Reminder</h1>

      <div className="form-container">
        <div className="input-group">
          <label htmlFor="medication-name" className="input-label">
            Medication Name:
          </label>
          <input
            id="medication-name"
            type="text"
            value={medicationName}
            onChange={(e) => setMedicationName(e.target.value)}
            placeholder="Enter medication name"
            className="input"
          />
        </div>

        <div className="time-repeat-group">
          <div className="input-group">
            <label htmlFor="medication-time" className="input-label">
              Time to Take:
            </label>
            <input
              id="medication-time"
              type="time"
              value={medicationTime}
              onChange={(e) => setMedicationTime(e.target.value)}
              className="input"
            />
          </div>

          <div className="input-group">
            <label htmlFor="repeat-every" className="input-label">
              Repeat Every (Hours):
            </label>
            <input
              id="repeat-every"
              type="number"
              value={repeatEvery}
              onChange={(e) => setRepeatEvery(Number(e.target.value))}
              min="1"
              className="input"
            />
          </div>
        </div>

        <button onClick={addMedication} className="add-button">
          Add Medication
        </button>
      </div>

      <div className="medications-list">
        <h2>Your Medications</h2>
        {medications.length > 0 ? (
          <ul className="medication-items">
            {medications.map((medication, index) => (
              <li key={index} className="medication-item">
                <div>
                  <span className="medication-name">{medication.name}</span> -
                  <span className="medication-time">{medication.time}</span> -
                  <span className="medication-repeat">
                    {medication.repeatEvery} hour(s)
                  </span>
                </div>
                <button
                  onClick={() => deleteMedication(index)}
                  className="delete-button"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>No medications added yet.</p>
        )}
      </div>
    </div>
  );
};

export default MedicationReminder;
