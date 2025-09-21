INSERT INTO locations (id, name, description)
SELECT *
FROM (
         VALUES
             (100, 'School', 'Where teachers educate and students learn'),
             (101, 'Newspaper Office', 'Where journalists write and publish news'),
             (102, 'Engineering Workshop', 'Where engineers design and build solutions'),
             (103, 'Restaurant', 'Where chefs create delicious meals'),
             (104, 'Farm', 'Where farmers grow crops and raise livestock'),
             (105, 'Construction Site', 'Where builders construct buildings and infrastructure'),
             (106, 'Art Studio', 'Where artists create paintings, sculptures, and crafts'),
             (107, 'Bank', 'Where bankers manage finances and provide financial services')
     ) AS v(id, name, description)
WHERE NOT EXISTS (
    SELECT 1
    FROM locations
    WHERE locations.name = v.name
);
