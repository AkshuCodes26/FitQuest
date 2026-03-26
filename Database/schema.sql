-- Create and use the database
CREATE DATABASE IF NOT EXISTS fitquest;
USE fitquest;

-- 1. USERS TABLE
CREATE TABLE Users (
    User_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Age INT NOT NULL,
    Gender ENUM('Male', 'Female', 'Other') NOT NULL,
    Height_cm FLOAT NOT NULL,
    Weight_kg FLOAT NOT NULL,
    BMI FLOAT GENERATED ALWAYS AS (Weight_kg / ((Height_cm / 100) * (Height_cm / 100))) STORED,
    Fitness_Goal ENUM('Weight Loss', 'Muscle Gain', 'Maintenance', 'Endurance') NOT NULL,
    Is_Injured BOOLEAN DEFAULT FALSE,
    Rest_Mode BOOLEAN DEFAULT FALSE,
    Email VARCHAR(150) UNIQUE NOT NULL,
    Password_Hash VARCHAR(255) NOT NULL,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. DIET TABLE
CREATE TABLE Diet (
    Diet_ID INT AUTO_INCREMENT PRIMARY KEY,
    Food_Name VARCHAR(150) NOT NULL,
    Calories FLOAT NOT NULL,
    Protein_g FLOAT DEFAULT 0,
    Carbs_g FLOAT DEFAULT 0,
    Fat_g FLOAT DEFAULT 0,
    Region_Type ENUM('North Indian', 'South Indian', 'Continental', 'Chinese', 'Other') NOT NULL,
    Meal_Type ENUM('Breakfast', 'Lunch', 'Dinner', 'Snack') NOT NULL
);

-- 3. EXERCISE TABLE
CREATE TABLE Exercise (
    Exercise_ID INT AUTO_INCREMENT PRIMARY KEY,
    Exercise_Name VARCHAR(150) NOT NULL,
    Duration_min INT NOT NULL,
    Calories_Burned FLOAT NOT NULL,
    Intensity ENUM('Low', 'Medium', 'High') NOT NULL,
    Exercise_Type ENUM('Cardio', 'Strength', 'Flexibility', 'Rest') NOT NULL
);

-- 4. ACTIVITY LOG TABLE
CREATE TABLE Activity_Log (
    Log_ID INT AUTO_INCREMENT PRIMARY KEY,
    User_ID INT NOT NULL,
    Log_Date DATE NOT NULL,
    Diet_ID INT,
    Exercise_ID INT,
    Calories_Consumed FLOAT DEFAULT 0,
    Water_Intake_L FLOAT DEFAULT 0,
    Exercise_Duration_min INT DEFAULT 0,
    Notes TEXT,
    FOREIGN KEY (User_ID) REFERENCES Users(User_ID) ON DELETE CASCADE,
    FOREIGN KEY (Diet_ID) REFERENCES Diet(Diet_ID) ON DELETE SET NULL,
    FOREIGN KEY (Exercise_ID) REFERENCES Exercise(Exercise_ID) ON DELETE SET NULL
);

-- 5. PROGRESS TABLE (Gamification)
CREATE TABLE Progress (
    Progress_ID INT AUTO_INCREMENT PRIMARY KEY,
    User_ID INT NOT NULL,
    Level_Status INT DEFAULT 1,
    Total_Points INT DEFAULT 0,
    Badge_Earned VARCHAR(100) DEFAULT NULL,
    Streak_Days INT DEFAULT 0,
    Last_Active_Date DATE,
    FOREIGN KEY (User_ID) REFERENCES Users(User_ID) ON DELETE CASCADE
);

-- 6. BADGES TABLE (for gamification rewards)
CREATE TABLE Badges (
    Badge_ID INT AUTO_INCREMENT PRIMARY KEY,
    Badge_Name VARCHAR(100) NOT NULL,
    Description TEXT,
    Points_Required INT NOT NULL,
    Icon_URL VARCHAR(255)
);

-- 7. USER BADGES (many-to-many: users <-> badges)
CREATE TABLE User_Badges (
    User_ID INT NOT NULL,
    Badge_ID INT NOT NULL,
    Earned_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (User_ID, Badge_ID),
    FOREIGN KEY (User_ID) REFERENCES Users(User_ID) ON DELETE CASCADE,
    FOREIGN KEY (Badge_ID) REFERENCES Badges(Badge_ID) ON DELETE CASCADE
);

-- =============================================
-- SAMPLE DATA
-- =============================================

-- Insert some badges
INSERT INTO Badges (Badge_Name, Description, Points_Required) VALUES
('7-Day Consistency', 'Complete goals for 7 consecutive days', 700),
('Calorie Control Champion', 'Stay within calorie goal for 30 days', 3000),
('Hydration Hero', 'Meet water intake target for 7 days', 500),
('First Step', 'Log your first workout', 100),
('Streak Master', 'Maintain a 30-day streak', 5000);

-- Insert sample exercises
INSERT INTO Exercise (Exercise_Name, Duration_min, Calories_Burned, Intensity, Exercise_Type) VALUES
('Walking', 30, 120, 'Low', 'Cardio'),
('Running', 30, 300, 'High', 'Cardio'),
('Yoga', 45, 150, 'Low', 'Flexibility'),
('Push-ups', 20, 100, 'Medium', 'Strength'),
('Meditation', 20, 30, 'Low', 'Rest'),
('Cycling', 30, 250, 'Medium', 'Cardio');

-- Insert sample diet items (Indian focused!)
INSERT INTO Diet (Food_Name, Calories, Protein_g, Carbs_g, Fat_g, Region_Type, Meal_Type) VALUES
('Idli (2 pieces)', 130, 4, 28, 0.5, 'South Indian', 'Breakfast'),
('Sambar', 80, 4, 12, 1.5, 'South Indian', 'Lunch'),
('Chapati (2)', 200, 6, 40, 3, 'North Indian', 'Dinner'),
('Dal Tadka', 150, 9, 20, 4, 'North Indian', 'Lunch'),
('Banana', 89, 1, 23, 0.3, 'Other', 'Snack'),
('Curd Rice', 220, 7, 40, 4, 'South Indian', 'Lunch');