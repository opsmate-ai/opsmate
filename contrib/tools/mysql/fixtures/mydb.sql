-- x-for-pet database schema and sample data
-- Drop the database if it exists
DROP DATABASE IF EXISTS `x-for-pet`;

-- Create the database
CREATE DATABASE `x-for-pet`;
USE `x-for-pet`;

-- Create the owners table
CREATE TABLE `owners` (
  `owner_id` INT PRIMARY KEY AUTO_INCREMENT,
  `first_name` VARCHAR(50) NOT NULL,
  `last_name` VARCHAR(50) NOT NULL,
  `email` VARCHAR(100) UNIQUE NOT NULL,
  `phone` VARCHAR(20),
  `address` VARCHAR(255),
  `city` VARCHAR(50),
  `state` VARCHAR(50),
  `zip_code` VARCHAR(20),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the pet_types table
CREATE TABLE `pet_types` (
  `type_id` INT PRIMARY KEY AUTO_INCREMENT,
  `name` VARCHAR(50) UNIQUE NOT NULL,
  `description` TEXT
);

-- Create the breeds table
CREATE TABLE `breeds` (
  `breed_id` INT PRIMARY KEY AUTO_INCREMENT,
  `type_id` INT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `description` TEXT,
  FOREIGN KEY (`type_id`) REFERENCES `pet_types`(`type_id`) ON DELETE CASCADE,
  UNIQUE KEY `unique_breed_per_type` (`type_id`, `name`)
);

-- Create the pets table
CREATE TABLE `pets` (
  `pet_id` INT PRIMARY KEY AUTO_INCREMENT,
  `owner_id` INT NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `type_id` INT NOT NULL,
  `breed_id` INT,
  `date_of_birth` DATE,
  `gender` ENUM('Male', 'Female', 'Unknown') NOT NULL DEFAULT 'Unknown',
  `color` VARCHAR(50),
  `weight_kg` DECIMAL(5,2),
  `microchip_id` VARCHAR(50) UNIQUE,
  `is_neutered` BOOLEAN DEFAULT FALSE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`owner_id`) REFERENCES `owners`(`owner_id`) ON DELETE CASCADE,
  FOREIGN KEY (`type_id`) REFERENCES `pet_types`(`type_id`),
  FOREIGN KEY (`breed_id`) REFERENCES `breeds`(`breed_id`)
);

-- Create the services table
CREATE TABLE `services` (
  `service_id` INT PRIMARY KEY AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `description` TEXT,
  `duration_minutes` INT,
  `price` DECIMAL(10,2) NOT NULL
);

-- Create the staff table
CREATE TABLE `staff` (
  `staff_id` INT PRIMARY KEY AUTO_INCREMENT,
  `first_name` VARCHAR(50) NOT NULL,
  `last_name` VARCHAR(50) NOT NULL,
  `position` VARCHAR(50) NOT NULL,
  `email` VARCHAR(100) UNIQUE NOT NULL,
  `phone` VARCHAR(20),
  `hire_date` DATE NOT NULL
);

-- Create the visits table
CREATE TABLE `visits` (
  `visit_id` INT PRIMARY KEY AUTO_INCREMENT,
  `pet_id` INT NOT NULL,
  `visit_date` DATETIME NOT NULL,
  `staff_id` INT,
  `reason` VARCHAR(255) NOT NULL,
  `diagnosis` TEXT,
  `treatment` TEXT,
  `notes` TEXT,
  `total_cost` DECIMAL(10,2),
  FOREIGN KEY (`pet_id`) REFERENCES `pets`(`pet_id`) ON DELETE CASCADE,
  FOREIGN KEY (`staff_id`) REFERENCES `staff`(`staff_id`)
);

-- Create the visit_services junction table
CREATE TABLE `visit_services` (
  `visit_service_id` INT PRIMARY KEY AUTO_INCREMENT,
  `visit_id` INT NOT NULL,
  `service_id` INT NOT NULL,
  `staff_id` INT,
  `notes` TEXT,
  `price` DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (`visit_id`) REFERENCES `visits`(`visit_id`) ON DELETE CASCADE,
  FOREIGN KEY (`service_id`) REFERENCES `services`(`service_id`),
  FOREIGN KEY (`staff_id`) REFERENCES `staff`(`staff_id`)
);

-- Create the prescriptions table
CREATE TABLE `prescriptions` (
  `prescription_id` INT PRIMARY KEY AUTO_INCREMENT,
  `visit_id` INT NOT NULL,
  `medication` VARCHAR(100) NOT NULL,
  `dosage` VARCHAR(100) NOT NULL,
  `instructions` TEXT NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE,
  FOREIGN KEY (`visit_id`) REFERENCES `visits`(`visit_id`) ON DELETE CASCADE
);

-- Insert sample data

-- Insert owners
INSERT INTO `owners` (`first_name`, `last_name`, `email`, `phone`, `address`, `city`, `state`, `zip_code`) VALUES
('John', 'Smith', 'john.smith@example.com', '555-123-4567', '123 Main St', 'Anytown', 'CA', '12345'),
('Emma', 'Johnson', 'emma.johnson@example.com', '555-987-6543', '456 Oak Ave', 'Somecity', 'NY', '67890'),
('Michael', 'Williams', 'michael.williams@example.com', '555-456-7890', '789 Pine Rd', 'Otherville', 'TX', '54321'),
('Sophia', 'Brown', 'sophia.brown@example.com', '555-246-8135', '101 Maple Dr', 'Somewhere', 'FL', '24680'),
('James', 'Davis', 'james.davis@example.com', '555-369-1472', '202 Cedar Ln', 'Anyplace', 'WA', '13579');

-- Insert pet types
INSERT INTO `pet_types` (`name`, `description`) VALUES
('Dog', 'Canine companion animal'),
('Cat', 'Feline companion animal'),
('Bird', 'Avian companion animal'),
('Rabbit', 'Lagomorph companion animal'),
('Fish', 'Aquatic companion animal');

-- Insert breeds
INSERT INTO `breeds` (`type_id`, `name`, `description`) VALUES
(1, 'Labrador Retriever', 'Friendly and outgoing breed known for its versatility'),
(1, 'German Shepherd', 'Intelligent and versatile working dog'),
(1, 'Beagle', 'Small scent hound with a friendly demeanor'),
(1, 'Poodle', 'Highly intelligent and elegantly-groomed breed'),
(2, 'Persian', 'Long-haired breed known for its sweet temperament'),
(2, 'Siamese', 'Vocal and social cat breed with distinctive coloring'),
(2, 'Maine Coon', 'Large, friendly cat breed with tufted ears'),
(3, 'Budgerigar', 'Small, colorful parakeet species'),
(3, 'Cockatiel', 'Small parrot with a distinctive crest'),
(4, 'Holland Lop', 'Dwarf rabbit breed with lopped ears');

-- Insert pets
INSERT INTO `pets` (`owner_id`, `name`, `type_id`, `breed_id`, `date_of_birth`, `gender`, `color`, `weight_kg`, `microchip_id`, `is_neutered`) VALUES
(1, 'Max', 1, 1, '2019-06-15', 'Male', 'Golden', 28.5, 'A123456789', TRUE),
(1, 'Luna', 2, 5, '2020-03-10', 'Female', 'White', 4.2, 'B987654321', TRUE),
(2, 'Bella', 1, 3, '2018-11-22', 'Female', 'Tri-color', 12.3, 'C456789123', TRUE),
(3, 'Charlie', 1, 2, '2020-09-05', 'Male', 'Black and Tan', 32.1, 'D789123456', FALSE),
(3, 'Lucy', 2, 6, '2021-01-17', 'Female', 'Seal Point', 3.8, 'E321654987', TRUE),
(4, 'Daisy', 4, 10, '2021-07-30', 'Female', 'Brown', 1.5, NULL, FALSE),
(4, 'Rocky', 3, 8, '2021-05-12', 'Male', 'Blue', 0.05, NULL, FALSE),
(5, 'Cooper', 1, 4, '2019-12-03', 'Male', 'White', 7.2, 'F654987321', TRUE),
(5, 'Chloe', 2, 7, '2020-08-21', 'Female', 'Tabby', 5.6, 'G147258369', TRUE);

-- Insert staff
INSERT INTO `staff` (`first_name`, `last_name`, `position`, `email`, `phone`, `hire_date`) VALUES
('Robert', 'Jones', 'Veterinarian', 'robert.jones@petclinic.com', '555-111-2222', '2018-05-15'),
('Lisa', 'Garcia', 'Veterinary Technician', 'lisa.garcia@petclinic.com', '555-333-4444', '2019-03-22'),
('David', 'Martinez', 'Receptionist', 'david.martinez@petclinic.com', '555-555-6666', '2020-01-10'),
('Jennifer', 'Wilson', 'Veterinarian', 'jennifer.wilson@petclinic.com', '555-777-8888', '2017-11-05'),
('Mark', 'Taylor', 'Groomer', 'mark.taylor@petclinic.com', '555-999-0000', '2021-02-28');

-- Insert services
INSERT INTO `services` (`name`, `description`, `duration_minutes`, `price`) VALUES
('Wellness Exam', 'Routine physical examination', 30, 50.00),
('Vaccination', 'Administration of preventive vaccines', 15, 25.00),
('Dental Cleaning', 'Professional teeth cleaning procedure', 60, 150.00),
('Spay/Neuter', 'Sterilization surgery', 90, 200.00),
('Microchipping', 'Implantation of identification microchip', 10, 45.00),
('Nail Trimming', 'Trimming of pet nails', 15, 20.00),
('Grooming', 'Full grooming service including bath, haircut, and nail trim', 60, 75.00),
('X-Ray', 'Diagnostic imaging', 30, 120.00),
('Blood Test', 'Laboratory analysis of blood sample', 20, 85.00),
('Fecal Exam', 'Laboratory analysis of stool sample', 15, 40.00);

-- Insert visits
INSERT INTO `visits` (`pet_id`, `visit_date`, `staff_id`, `reason`, `diagnosis`, `treatment`, `notes`, `total_cost`) VALUES
(1, '2023-03-15 10:30:00', 1, 'Annual checkup', 'Healthy', 'Vaccinations updated', 'Weight slightly above ideal range', 75.00),
(2, '2023-03-20 14:45:00', 4, 'Vomiting', 'Hairball', 'Hairball remedy prescribed', 'Recommended brushing daily', 50.00),
(3, '2023-04-05 09:15:00', 1, 'Limping', 'Mild sprain', 'Rest and anti-inflammatory medication', 'Recheck in 2 weeks if not improved', 95.00),
(5, '2023-04-12 11:00:00', 4, 'Ear infection', 'Bacterial otitis', 'Ear drops and antibiotics', 'Ears need regular cleaning', 120.00),
(8, '2023-04-18 16:30:00', 1, 'Dental issues', 'Periodontal disease', 'Dental cleaning scheduled', 'Recommended dental chews', 50.00),
(1, '2023-05-02 13:00:00', 1, 'Dental cleaning', 'Moderate tartar buildup', 'Full dental cleaning performed', 'No extractions needed', 150.00),
(4, '2023-05-10 10:00:00', 4, 'New pet checkup', 'Healthy, needs vaccines', 'Initial vaccine series started', 'Microchipping recommended', 110.00);

-- Insert visit services
INSERT INTO `visit_services` (`visit_id`, `service_id`, `staff_id`, `notes`, `price`) VALUES
(1, 1, 1, 'Annual wellness exam', 50.00),
(1, 2, 2, 'DHPP booster', 25.00),
(2, 1, 4, 'Sick visit examination', 50.00),
(3, 1, 1, 'Lameness examination', 50.00),
(3, 9, 2, 'Blood panel to check inflammation', 45.00),
(4, 1, 4, 'Ear examination', 50.00),
(4, 9, 2, 'Culture and sensitivity test', 70.00),
(5, 1, 1, 'Dental examination', 50.00),
(6, 3, 1, 'Complete dental cleaning', 150.00),
(7, 1, 4, 'New patient examination', 50.00),
(7, 2, 2, 'First set of vaccines', 40.00),
(7, 5, 2, 'Microchip implantation', 20.00);

-- Insert prescriptions
INSERT INTO `prescriptions` (`visit_id`, `medication`, `dosage`, `instructions`, `start_date`, `end_date`) VALUES
(2, 'Laxatone', '1 tsp', 'Administer orally once daily', '2023-03-20', '2023-03-27'),
(3, 'Carprofen', '25mg', 'Give 1 tablet every 12 hours with food', '2023-04-05', '2023-04-19'),
(4, 'Baytril Otic', '5 drops', 'Apply to affected ear twice daily after cleaning', '2023-04-12', '2023-04-26'),
(4, 'Amoxicillin', '50mg', 'Give 1 tablet twice daily with food', '2023-04-12', '2023-04-22');

-- Add indexes for better performance
CREATE INDEX idx_pets_owner_id ON pets(owner_id);
CREATE INDEX idx_pets_type_id ON pets(type_id);
CREATE INDEX idx_pets_breed_id ON pets(breed_id);
CREATE INDEX idx_visits_pet_id ON visits(pet_id);
CREATE INDEX idx_visits_staff_id ON visits(staff_id);
CREATE INDEX idx_visit_services_visit_id ON visit_services(visit_id);
CREATE INDEX idx_visit_services_service_id ON visit_services(service_id);
CREATE INDEX idx_prescriptions_visit_id ON prescriptions(visit_id);
