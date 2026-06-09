from sqlalchemy.orm import Session
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter

NCERT_SYLLABUS = [
    # --- PRIMARY CLASSES (1-5) ---
    {
        "class_name": "Grade 1",
        "grade": "1",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH1",
                "chapters": [
                    {"number": "1", "title": "Shapes and Space", "content": "Spatial vocabulary (inside-outside, near-far, top-bottom, under-on) and basic 2D and 3D shapes."},
                    {"number": "2", "title": "Numbers from One to Nine", "content": "Introduction to numbers, counting objects, writing digits, and comparing quantities."},
                    {"number": "3", "title": "Addition", "content": "Adding single-digit numbers, counting objects together, and basic addition word problems."},
                    {"number": "4", "title": "Subtraction", "content": "Taking away objects, single-digit subtraction, and simple subtraction problems."},
                    {"number": "5", "title": "Numbers from Ten to Twenty", "content": "Introduction to two-digit numbers, place value of tens and ones, and counting up to 20."},
                    {"number": "6", "title": "Time", "content": "Concept of time, sequences of daily activities (morning, afternoon, night, daily routines)."},
                    {"number": "7", "title": "Measurement", "content": "Comparison of lengths (longer-shorter, taller-shorter) and weights (heavier-lighter)."},
                    {"number": "8", "title": "Numbers from Twenty-one to Fifty", "content": "Counting, writing, and place values for numbers up to 50."},
                    {"number": "9", "title": "Data Handling", "content": "Organizing objects into groups, counting items, and simple visual lists."},
                    {"number": "10", "title": "Patterns", "content": "Recognizing and completing simple visual and numerical sequences."},
                    {"number": "11", "title": "Numbers", "content": "Practice counting, writing, and place values for numbers 50 to 99."},
                    {"number": "12", "title": "Money", "content": "Identification of standard Indian coins and notes, and basic shopping scenarios."},
                    {"number": "13", "title": "How Many", "content": "Recap of counting, identifying quantities, and using numbers in real-world contexts."}
                ]
            },
            {
                "name": "English",
                "code": "ENG1",
                "chapters": [
                    {"number": "1", "title": "A Happy Child", "content": "A poem about a child's happy day, green trees, sunshine, and playtime."},
                    {"number": "2", "title": "After a Bath", "content": "Exploring daily hygiene routines, wiping clean, and self-care after bathing."},
                    {"number": "3", "title": "One Little Kitten", "content": "A counting poem exploring numbers 1 to 15 and different types of animals."},
                    {"number": "4", "title": "Once I Saw a Little Bird", "content": "A story about interacting with nature, birds, and learning kindness."},
                    {"number": "5", "title": "Merry-Go-Round", "content": "Exploring playing at the fair, riding rides, and circles."},
                    {"number": "6", "title": "If I Were an Apple", "content": "Imaginative poetry about trees, fruit, and the joy of sharing with others."},
                    {"number": "7", "title": "A Kite", "content": "A poem about flying in the sky, standard winds, and wishing to fly high."},
                    {"number": "8", "title": "A Little Turtle", "content": "A story about a slow-moving turtle carrying its shell home."},
                    {"number": "9", "title": "Clouds", "content": "A poem about rain, clouds, cooling weather changes, and singing."},
                    {"number": "10", "title": "Flying-Man", "content": "A poem about a flying superhero and asking him where he flies."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 2",
        "grade": "2",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH2",
                "chapters": [
                    {"number": "1", "title": "What is Long, What is Round?", "content": "Exploring attributes of shapes, long vs. round, roll and slide concepts."},
                    {"number": "2", "title": "Counting in Groups", "content": "Grouping items to count quickly (pairs, tens), and estimation."},
                    {"number": "3", "title": "How Much Can You Carry?", "content": "Understanding weight, heavy and light items, and balance comparison."},
                    {"number": "4", "title": "Counting in Tens", "content": "Concept of place value, grouping items in bundles of tens and leftover ones."},
                    {"number": "5", "title": "Patterns", "content": "Identifying and continuing repeating shapes, colors, and number patterns."},
                    {"number": "6", "title": "Footprints", "content": "Tracing footprints and outlines of everyday objects to identify shapes."},
                    {"number": "7", "title": "Jugs and Mugs", "content": "Understanding volume, capacity, and estimation of liquid quantities."},
                    {"number": "8", "title": "Tens and Ones", "content": "Breaking down two-digit numbers into tens and ones, using money notes."},
                    {"number": "9", "title": "My Funday", "content": "Days of the week, school timetable, calendar concepts, and seasons."},
                    {"number": "10", "title": "Add our Points", "content": "Adding multiple single-digit numbers together in games and sports context."},
                    {"number": "11", "title": "Lines and Lines", "content": "Straight, curved, slanting, horizontal, and vertical lines in art and writing."},
                    {"number": "12", "title": "Give and Take", "content": "Two-digit addition and subtraction with carryover and borrowing."},
                    {"number": "13", "title": "The Longest Step", "content": "Measuring length using non-standard units like handspans, footsteps, and fingers."},
                    {"number": "14", "title": "Birds Come, Birds Go", "content": "Word problems involving addition and subtraction up to 100, counting birds."},
                    {"number": "15", "title": "How Many Pigtails?", "content": "Counting and organizing simple datasets based on hair styles and clothing features."}
                ]
            },
            {
                "name": "English",
                "code": "ENG2",
                "chapters": [
                    {"number": "1", "title": "First Day at School", "content": "A child's thoughts, feelings, and questions on their first day of school."},
                    {"number": "2", "title": "Haldi's Adventure", "content": "A girl meets a talking giraffe named Smiley on her way to school and learns about learning."},
                    {"number": "3", "title": "I am Lucky", "content": "A poem expressing gratitude for being oneself and appreciating animal traits."},
                    {"number": "4", "title": "I Want", "content": "A little monkey wants to be strong like other animals and gets help from a wise woman."},
                    {"number": "5", "title": "A Smile", "content": "A poem about how a smile is a funny thing that spreads happiness all around."},
                    {"number": "6", "title": "The Wind and the Sun", "content": "A contest between the wind and the sun to see who can make a traveler take off his coat."},
                    {"number": "7", "title": "Rain", "content": "A simple poem about rain falling all around on umbrellas, trees, and ships at sea."},
                    {"number": "8", "title": "Storm in the Garden", "content": "Sunu-Sunu the snail visits his friends the ants during a storm and stays safe."},
                    {"number": "9", "title": "Mr. Nobody", "content": "A funny poem about a quiet little man who does all the mischief in everyone's house."},
                    {"number": "10", "title": "Curlylocks and the Three Bears", "content": "A girl enters the cottage of a bear family and tries their porridge, chairs, and beds."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 3",
        "grade": "3",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH3",
                "chapters": [
                    {"number": "1", "title": "Where to Look From", "content": "Viewing objects from different angles (top, side, front), symmetry, and mirror halves."},
                    {"number": "2", "title": "Fun with Numbers", "content": "Counting beyond 100, number names, place value up to three digits, and number patterns."},
                    {"number": "3", "title": "Give and Take", "content": "Adding and subtracting two-digit and three-digit numbers mentally and using grid charts."},
                    {"number": "4", "title": "Long and Short", "content": "Measuring length in centimeters and meters, estimating distances, and using rulers."},
                    {"number": "5", "title": "Shapes and Designs", "content": "Edges, corners, 2D shapes, tangrams, and tiling patterns."},
                    {"number": "6", "title": "Fun with Give and Take", "content": "Solving addition and subtraction word problems, and checking subtraction using addition."},
                    {"number": "7", "title": "Time Goes On...", "content": "Reading calendars, measuring durations (minutes, hours, days), birth certificates, and clocks."},
                    {"number": "8", "title": "Who is Heavier?", "content": "Comparing weights in grams and kilograms, and using balance scales."},
                    {"number": "9", "title": "How Many Times?", "content": "Introduction to multiplication as repeated addition, and multiplication tables."},
                    {"number": "10", "title": "Play with Patterns", "content": "Recognizing and creating visual, alphabetical, and numeric patterns."},
                    {"number": "11", "title": "Jugs and Mugs", "content": "Capacity, measuring liquids in liters and milliliters, and pouring volumes."},
                    {"number": "12", "title": "Can We Share?", "content": "Introduction to division as equal sharing and grouping, and its relationship with multiplication."},
                    {"number": "13", "title": "Smart Charts", "content": "Organizing data using tally marks, pictographs, and simple charts."},
                    {"number": "14", "title": "Rupees and Paise", "content": "Money conversions, making cash memos/bills, and solving monetary word problems."}
                ]
            },
            {
                "name": "Environmental Studies",
                "code": "EVS3",
                "chapters": [
                    {"number": "1", "title": "Poonam's Day out", "content": "Observing animals in local surroundings, and classifying them based on movement and habitat."},
                    {"number": "2", "title": "The Plant Fairy", "content": "Identifying different types of plants, leaves, and trees through sensory activities."},
                    {"number": "3", "title": "Water O' Water!", "content": "Importance of water, sources of water, water cycle songs, and conservation."},
                    {"number": "4", "title": "Our First School", "content": "The role of family as our first school, family relationships, and habits."},
                    {"number": "5", "title": "Chhotu's House", "content": "Understanding houses, rooms, cleanliness, and decorating houses for festivals."},
                    {"number": "6", "title": "Foods We Eat", "content": "Different types of food eaten by people of various ages, cultures, and regions."},
                    {"number": "7", "title": "Saying without Speaking", "content": "Sign language, expressing feelings through facial expressions (mudras) and gestures."},
                    {"number": "8", "title": "Flying High", "content": "Characteristics of different birds, their feathers, beaks, sounds, and habitats."},
                    {"number": "9", "title": "It's Raining", "content": "Importance of rain for plants and animals, cloud formation, and story of elephants."},
                    {"number": "10", "title": "What is Cooking", "content": "Cooking methods (boiling, baking, frying), utensils, fuels, and raw vs. cooked food."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 4",
        "grade": "4",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH4",
                "chapters": [
                    {"number": "1", "title": "Building with Bricks", "content": "Brick patterns, arch designs, historical monuments, and counting large numbers of bricks."},
                    {"number": "2", "title": "Long and Short", "content": "Measuring distances, converting units (km to m, m to cm), and tracking sports running records."},
                    {"number": "3", "title": "A Trip to Bhopal", "content": "Solving real-world math word problems involving calculations of speed, time, distance, and ticket money."},
                    {"number": "4", "title": "Tick-Tick-Tick", "content": "Telling time, using 12-hour and 24-hour clocks, timelines, calendars, and duration calculations."},
                    {"number": "5", "title": "The Way The World Looks", "content": "Perspective drawings (top view vs side view), mapping layouts, and folding 3D shapes."},
                    {"number": "6", "title": "The Junk Seller", "content": "Basic business concepts, cost price, selling price, profit, loss, loans, and interest calculations."},
                    {"number": "7", "title": "Jugs and Mugs", "content": "Measuring liquid volumes, solving word problems on capacity, and addition/subtraction of liters."},
                    {"number": "8", "title": "Carts and Wheels", "content": "Circle parts (radius, diameter, center, circumference), and tracing circles using compasses."},
                    {"number": "9", "title": "Halves and Quarters", "content": "Fractions, dividing shapes, weights, and numbers into equal parts (1/2, 1/4, 3/4)."},
                    {"number": "10", "title": "Play with Patterns", "content": "Visual patterns, coding-decoding, secret messages, and repeating numeric patterns."}
                ]
            },
            {
                "name": "Environmental Studies",
                "code": "EVS4",
                "chapters": [
                    {"number": "1", "title": "Going to School", "content": "Different transport methods children use to reach school (bamboo bridges, trolley, vallam, camel cart)."},
                    {"number": "2", "title": "Ear to Ear", "content": "Animal ears, skin patterns, and classifications of birds, mammals, and reptiles based on ears/hair."},
                    {"number": "3", "title": "A Day with Nandu", "content": "Elephants' lives, herd dynamics, food habits, and behaviors of baby elephants."},
                    {"number": "4", "title": "The Story of Amrita", "content": "Environmental conservation, Khejadi trees, and the history of the Bishnoi village sacrifice."},
                    {"number": "5", "title": "Anita and the Honeybees", "content": "Beekeeping, life cycle of bees, and a girl's journey to pursue higher education."},
                    {"number": "6", "title": "Omana's Journey", "content": "Train travel, planning, packing, railway stations, and writing travel logs."},
                    {"number": "7", "title": "From the Window", "content": "Changing landscapes, bridges, tunnels, and states of India (Goa to Kerala)."},
                    {"number": "8", "title": "Reaching Grandmother's House", "content": "Different local transports in Kerala (ferries, buses, auto-rickshaws), and reading tickets."},
                    {"number": "9", "title": "Changing Families", "content": "Births, marriages, job transfers, and how they impact family structures and roles."},
                    {"number": "10", "title": "Hu Tu Tu, Hu Tu Tu", "content": "Rules and sportsmanship through Kabaddi, and the stories of sports women."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 5",
        "grade": "5",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH5",
                "chapters": [
                    {"number": "1", "title": "The Fish Tale", "content": "Introduction to large numbers (lakhs, crores), word problems involving fish markets, boat speeds, and cooperative banks."},
                    {"number": "2", "title": "Shapes and Angles", "content": "Right angles, acute angles, obtuse angles, angles in names, clocks, and structural stability."},
                    {"number": "3", "title": "How Many Squares?", "content": "Grid structure calculation, area of rectangles and triangles, perimeter, and puzzle design."},
                    {"number": "4", "title": "Parts and Wholes", "content": "Fractions, numerator/denominator, equivalent fractions, patterns in flags, and cooking recipes."},
                    {"number": "5", "title": "Does it Look the Same?", "content": "Reflection symmetry, mirror lines, rotational symmetry (half-turn, quarter-turn, one-third turn)."},
                    {"number": "6", "title": "Be My Multiple, I'll be Your Factor", "content": "Multiples, common multiples, factors, common factors, and drawing factor trees."},
                    {"number": "7", "title": "Can You See the Pattern?", "content": "Numeric patterns, magic squares, magic hexagons, palindrome numbers, and calendar pattern tricks."},
                    {"number": "8", "title": "Mapping Your Way", "content": "Map reading, scales, routes, directions, and aerial photography perspective."},
                    {"number": "9", "title": "Boxes and Sketches", "content": "Net drawings of 3D shapes, drawing cubes/prisms, and creating layout plans for houses."},
                    {"number": "10", "title": "Tenths and Hundredths", "content": "Decimals, place value, converting centimeters to millimeters, and measuring fine objects."}
                ]
            },
            {
                "name": "Environmental Studies",
                "code": "EVS5",
                "chapters": [
                    {"number": "1", "title": "Super Senses", "content": "Animal senses (sight, smell, hearing), animal communication, tiger behavior, and poaching threats."},
                    {"number": "2", "title": "A Snake Charmer's Story", "content": "Life and culture of Kalbelia snake charmers, traditional medicine, and animal welfare laws."},
                    {"number": "3", "title": "From Tasting to Digesting", "content": "Tongue taste buds, digestion process, stomach juices discovery, balanced diet, and starvation."},
                    {"number": "4", "title": "Mangoes Round the Year", "content": "Food preservation methods (pickling, drying), spoilage, and making Mamidi Tandra (mango leather)."},
                    {"number": "5", "title": "Seeds and Seeds", "content": "Seed structure, germination requirements, seed dispersal (wind, water, animals), pitcher plants."},
                    {"number": "6", "title": "Every Drop Counts", "content": "Water management history, stepwells (baolis), lakes (Ghadsisar), and rainwater harvesting."},
                    {"number": "7", "title": "Experiments with Water", "content": "Floating and sinking, solubility of substances, evaporation, and properties of the Dead Sea."},
                    {"number": "8", "title": "A Treat for Mosquitoes", "content": "Malaria symptoms, lifecycle of mosquitoes, anemia, and discovery of Ronald Ross."},
                    {"number": "9", "title": "Up You Go!", "content": "Mountaineering camp leadership, rock climbing, shelter build, and Bachhendri Pal's achievements."},
                    {"number": "10", "title": "Walls Tell Stories", "content": "Golconda Fort history, old water wheel mechanisms, weapons, and museum study."}
                ]
            }
        ]
    },

    # --- MIDDLE CLASSES (6-8) ---
    {
        "class_name": "Grade 6",
        "grade": "6",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH6",
                "chapters": [
                    {"number": "1", "title": "Knowing Our Numbers", "content": "Exploring large numbers up to crores, estimation, placement of commas, brackets, and Roman numerals."},
                    {"number": "2", "title": "Whole Numbers", "content": "Understanding natural numbers, whole numbers, predecessors, successors, number lines, and mathematical properties."},
                    {"number": "3", "title": "Playing with Numbers", "content": "Factors, multiples, prime/composite/co-prime numbers, divisibility tests, prime factorization, HCF and LCM."},
                    {"number": "4", "title": "Basic Geometrical Ideas", "content": "Introduction to points, lines, line segments, rays, curves, polygons, angles, triangles, quadrilaterals, and circles."},
                    {"number": "5", "title": "Understanding Elementary Shapes", "content": "Measuring line segments, classifying angles (acute, right, obtuse, reflex), perpendicular lines, triangles, quadrilaterals, and 3D shapes."},
                    {"number": "6", "title": "Integers", "content": "Concept of negative numbers, integers, representation on number lines, and addition and subtraction of integers."},
                    {"number": "7", "title": "Fractions", "content": "Fractions on a number line, proper/improper/mixed fractions, equivalent fractions, simplest form, and comparing/adding fractions."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI6",
                "chapters": [
                    {"number": "1", "title": "Components of Food", "content": "Nutrients (carbohydrates, fats, proteins, vitamins, minerals), balanced diet, roughage, and deficiency diseases."},
                    {"number": "2", "title": "Sorting Materials into Groups", "content": "Classifying materials based on appearance, hardness, solubility, floatation, transparency, and conductivity."},
                    {"number": "3", "title": "Separation of Substances", "content": "Sieving, winnowing, handpicking, sedimentation, decantation, filtration, evaporation, and condensation."},
                    {"number": "4", "title": "Getting to Know Plants", "content": "Classification of herbs, shrubs, trees, creepers, and climbers. Structures of stems, leaves, roots, and flowers."},
                    {"number": "5", "title": "Body Movements", "content": "Human skeletal system, joints (ball-and-socket, hinge, pivotal, fixed), cartilage, muscle function, and animal locomotion."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 7",
        "grade": "7",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH7",
                "chapters": [
                    {"number": "1", "title": "Integers", "content": "Properties of addition, subtraction, multiplication, and division of integers, BODMAS, and word problems."},
                    {"number": "2", "title": "Fractions and Decimals", "content": "Multiplication and division of fractions, reciprocal of fractions, multiplication/division of decimals, and word problems."},
                    {"number": "3", "title": "Data Handling", "content": "Arithmetic mean, median, mode of ungrouped data, range, bar graphs, double bar graphs, and probability."},
                    {"number": "4", "title": "Simple Equations", "content": "Setting up equations, solving equations using balancing and transposition methods, and application to word problems."},
                    {"number": "5", "title": "Lines and Angles", "content": "Complementary, supplementary, adjacent, vertically opposite angles, linear pairs, parallel lines, and transversals."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI7",
                "chapters": [
                    {"number": "1", "title": "Nutrition in Plants", "content": "Autotrophic nutrition, photosynthesis requirements, saprotrophs, parasitic plants, symbiotic relationship, and soil replenishment."},
                    {"number": "2", "title": "Nutrition in Animals", "content": "Steps of nutrition, human digestive system (mouth, esophagus, stomach, intestines), digestion in grass-eaters, and Amoeba feeding."},
                    {"number": "3", "title": "Heat", "content": "Hot and cold concepts, clinical and laboratory thermometers, conduction, convection, radiation, and sea/land breezes."},
                    {"number": "4", "title": "Acids, Bases and Salts", "content": "Properties of organic and mineral acids, strong/weak bases, indicators (litmus, turmeric, china rose), and neutralization reaction."},
                    {"number": "5", "title": "Physical and Chemical Changes", "content": "Reversible physical alterations, chemical reactions with new substances, rusting of iron, and crystallization process."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 8",
        "grade": "8",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH8",
                "chapters": [
                    {"number": "1", "title": "Rational Numbers", "content": "Properties of rational numbers (closure, commutativity, associativity, distributivity), additive/multiplicative identity and inverse, and density property."},
                    {"number": "2", "title": "Linear Equations in One Variable", "content": "Solving equations with linear expressions on one side and numbers on the other, equations reducible to linear form, and applications."},
                    {"number": "3", "title": "Understanding Quadrilaterals", "content": "Polygons classification, angle sum property, exterior angles sum, types of quadrilaterals (trapezium, kite, parallelogram, rhombus, rectangle, square)."},
                    {"number": "4", "title": "Data Handling", "content": "Organizing data, group frequency distributions, histograms, circle graphs/pie charts, and basic probability concepts."},
                    {"number": "5", "title": "Squares and Square Roots", "content": "Properties of square numbers, finding square roots through prime factorization, division method, and decimal square roots."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI8",
                "chapters": [
                    {"number": "1", "title": "Crop Production and Management", "content": "Agricultural practices, sowing, irrigation methods, weeding, harvesting, storage, animal husbandry, and fertilizers vs manure."},
                    {"number": "2", "title": "Microorganisms: Friend and Foe", "content": "Classification (bacteria, fungi, protozoa, algae, viruses), commercial/medicinal uses, vaccines, food preservation, and nitrogen cycle."},
                    {"number": "3", "title": "Coal and Petroleum", "content": "Natural resources, fossil fuels, fractional distillation of petroleum, coal tar, coal gas, and natural gas conservation."},
                    {"number": "4", "title": "Combustion and Flame", "content": "Conditions for combustion, ignition temperature, inflammable substances, fire control, types of combustion, and zones of a candle flame."},
                    {"number": "5", "title": "Conservation of Plants and Animals", "content": "Deforestation impacts, biosphere reserves, wildlife sanctuaries, national parks, red data book, migration, and reforestation."}
                ]
            }
        ]
    },

    # --- SECONDARY CLASSES (9-10) ---
    {
        "class_name": "Grade 9",
        "grade": "9",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH9",
                "chapters": [
                    {"number": "1", "title": "Number Systems", "content": "Irrational numbers, real numbers and decimal expansions, representing real numbers on number lines, operations on real numbers, and laws of exponents."},
                    {"number": "2", "title": "Polynomials", "content": "Polynomials in one variable, zeroes of a polynomial, remainder theorem, factor theorem, factorization of polynomials, and algebraic identities."},
                    {"number": "3", "title": "Coordinate Geometry", "content": "Cartesian system, plotting a point in a plane if its coordinates are given, quadrant signs, and axes concepts."},
                    {"number": "4", "title": "Linear Equations in Two Variables", "content": "Linear equations, solution of a linear equation, graph of a linear equation in two variables, and equations of lines parallel to x-axis and y-axis."},
                    {"number": "5", "title": "Lines and Angles", "content": "Basic terms, intersecting/non-intersecting lines, pairs of angles, parallel lines and transversal, lines parallel to same line, and angle sum of a triangle."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI9",
                "chapters": [
                    {"number": "1", "title": "Matter in Our Surroundings", "content": "Physical nature of matter, characteristics of particles, states of matter (solid, liquid, gas), effect of temperature/pressure change, and evaporation."},
                    {"number": "2", "title": "Is Matter Around Us Pure?", "content": "Mixtures, solutions, suspensions, colloidal systems, separating components of mixtures, physical/chemical changes, elements, and compounds."},
                    {"number": "3", "title": "Atoms and Molecules", "content": "Laws of chemical combination, Dalton's atomic theory, atomic mass, molecular mass, chemical formula writing, and mole concept."},
                    {"number": "4", "title": "Structure of the Atom", "content": "Charged particles in matter, Thomson/Rutherford/Bohr atomic models, electron distribution, valency, atomic number, mass number, isotopes, and isobars."},
                    {"number": "5", "title": "The Fundamental Unit of Life", "content": "Discovery of cell, plasma membrane, cell wall, nucleus, cytoplasm, cell organelles (endoplasmic reticulum, golgi apparatus, mitochondria, plastids, vacuoles)."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 10",
        "grade": "10",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH10",
                "chapters": [
                    {"number": "1", "title": "Real Numbers", "content": "Fundamental Theorem of Arithmetic, decimal expansions of rational numbers, and proof of irrationality (e.g., root 2, root 3, root 5)."},
                    {"number": "2", "title": "Polynomials", "content": "Geometrical meaning of zeroes of a polynomial, relationship between zeroes and coefficients of quadratic and cubic polynomials, and division algorithm."},
                    {"number": "3", "title": "Pair of Linear Equations in Two Variables", "content": "Graphical method of solution, algebraic methods (substitution, elimination, cross-multiplication), and equations reducible to linear form."},
                    {"number": "4", "title": "Quadratic Equations", "content": "Standard form, solution by factorization, completing the square, quadratic formula, nature of roots, and real-life applications."},
                    {"number": "5", "title": "Arithmetic Progressions", "content": "nth term of an AP, sum of first n terms of an AP, common difference, and solving daily life AP applications."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI10",
                "chapters": [
                    {"number": "1", "title": "Chemical Reactions and Equations", "content": "Chemical equations balancing, combination, decomposition, single displacement, double displacement, precipitation, oxidation, reduction, rancidity, and corrosion."},
                    {"number": "2", "title": "Acids, Bases and Salts", "content": "Chemical properties of acids/bases, pH scale, importance of pH in everyday life, sodium hydroxide, bleaching powder, baking/washing soda, and plaster of paris."},
                    {"number": "3", "title": "Metals and Non-metals", "content": "Physical/chemical properties of metals/non-metals, reactivity series, ionic compounds formation/properties, basic metallurgy, and corrosion prevention."},
                    {"number": "4", "title": "Life Processes", "content": "Autotrophic/heterotrophic nutrition in plants/animals, human respiration, transport in plants/humans, and excretory systems in plants/animals."},
                    {"number": "5", "title": "Control and Coordination", "content": "Nervous system, reflex action, human brain, hormones in animals, plant hormones (auxins, gibberellins, abscisic acid), and tropic movements."}
                ]
            }
        ]
    },

    # --- SENIOR SECONDARY CLASSES (11-12) ---
    {
        "class_name": "Grade 11",
        "grade": "11",
        "section": "A",
        "subjects": [
            {
                "name": "Physics",
                "code": "PHY11",
                "chapters": [
                    {"number": "1", "title": "Units and Measurements", "content": "SI units, fundamental and derived units, dimensional analysis, errors in measurement, and significant figures."},
                    {"number": "2", "title": "Motion in a Straight Line", "content": "Frame of reference, displacement, velocity, acceleration, uniform/non-uniform motion, position-time graphs, and kinematic equations."},
                    {"number": "3", "title": "Motion in a Plane", "content": "Vector addition/subtraction, resolution, projectile motion, uniform circular motion, and relative velocity in two dimensions."},
                    {"number": "4", "title": "Laws of Motion", "content": "Newton's laws of motion, conservation of linear momentum, equilibrium of concurrent forces, static and kinetic friction, and uniform circular motion dynamics."},
                    {"number": "5", "title": "Work, Energy and Power", "content": "Work-energy theorem, potential/kinetic energy, conservative/non-conservative forces, elastic/inelastic collisions, and power calculations."}
                ]
            },
            {
                "name": "Chemistry",
                "code": "CHM11",
                "chapters": [
                    {"number": "1", "title": "Some Basic Concepts of Chemistry", "content": "Laws of chemical combination, atomic and molecular masses, mole concept, empirical and molecular formulas, stoichiometry, and limiting reagents."},
                    {"number": "2", "title": "Structure of Atom", "content": "Discovery of subatomic particles, Bohr's model, dual nature of matter, Heisenberg uncertainty principle, quantum numbers, and electron configuration."},
                    {"number": "3", "title": "Classification of Elements and Periodicity", "content": "Modern periodic law, s/p/d/f block elements, periodic trends in properties (atomic radii, ionization enthalpy, electron gain enthalpy, electronegativity)."},
                    {"number": "4", "title": "Chemical Bonding and Molecular Structure", "content": "Valence electrons, ionic and covalent bonds, Lewis structure, VSEPR theory, hybridization (sp, sp2, sp3), and molecular orbital theory."},
                    {"number": "5", "title": "Chemical Thermodynamics", "content": "System and surroundings, extensive/intensive properties, state functions, first law, enthalpy, heat capacity, Hess's law, entropy, and Gibbs free energy."}
                ]
            },
            {
                "name": "Biology",
                "code": "BIO11",
                "chapters": [
                    {"number": "1", "title": "The Living World", "content": "Characteristics of living organisms, biodiversity, taxonomy, systematic categories, binomial nomenclature, and taxonomical aids (herbarium, botanical gardens, museums)."},
                    {"number": "2", "title": "Biological Classification", "content": "Five kingdom classification system (Monera, Protista, Fungi, Plantae, Animalia), lichens, viruses, and viroids structure and features."},
                    {"number": "3", "title": "Plant Kingdom", "content": "Algae, Bryophytes, Pteridophytes, Gymnosperms, Angiosperms classification, lifecycle patterns, and alternation of generations."},
                    {"number": "4", "title": "Animal Kingdom", "content": "Basis of classification (symmetry, coelom, segmentation), non-chordate phyla characteristics, and chordate classes structure."},
                    {"number": "5", "title": "Cell: The Unit of Life", "content": "Cell theory, prokaryotic vs eukaryotic cell, structure of plasma membrane, cell wall, nucleus, endomembrane system, mitochondria, chloroplasts, and cytoskeleton."}
                ]
            },
            {
                "name": "Mathematics",
                "code": "MATH11",
                "chapters": [
                    {"number": "1", "title": "Sets", "content": "Sets and their representations, empty set, finite and infinite sets, equal sets, subsets, power sets, universal sets, Venn diagrams, and union/intersection operations."},
                    {"number": "2", "title": "Relations and Functions", "content": "Ordered pairs, Cartesian product of sets, relations, domain, codomain, range, functions, types, and algebra of real functions."},
                    {"number": "3", "title": "Trigonometric Functions", "content": "Positive and negative angles, radian and degree measures, trigonometric identities, graphs of trigonometric functions, and trigonometric equations."},
                    {"number": "4", "title": "Permutations and Combinations", "content": "Fundamental principle of counting, factorial n, permutations formula nPr, combinations formula nCr, and practical word problems."},
                    {"number": "5", "title": "Limits and Derivatives", "content": "Intuitive understanding of limits, standard limits, algebra of limits, derivatives of polynomials, trigonometric functions, and rate of change."}
                ]
            }
        ]
    },
    {
        "class_name": "Grade 12",
        "grade": "12",
        "section": "A",
        "subjects": [
            {
                "name": "Physics",
                "code": "PHY12",
                "chapters": [
                    {"number": "1", "title": "Electric Charges and Fields", "content": "Coulomb's law, electric field, electric field lines, electric dipole, electric flux, Gauss's law, and its electrostatic applications."},
                    {"number": "2", "title": "Electrostatic Potential and Capacitance", "content": "Electrostatic potential, potential energy, conductors, dielectrics and polarization, capacitors, parallel plate capacitor, and combination of capacitors."},
                    {"number": "3", "title": "Current Electricity", "content": "Ohm's law, drift velocity, resistivity, temperature dependence, Kirchhoff's rules, Wheatstone bridge, potentiometer, and cells in series/parallel."},
                    {"number": "4", "title": "Moving Charges and Magnetism", "content": "Biot-Savart law, Ampere's circuital law, force on moving charges/currents, cyclotron, galvanometer conversion, and toroid/solenoid magnetic fields."},
                    {"number": "5", "title": "Electromagnetic Induction", "content": "Faraday's laws of induction, Lenz's law, motional electromotive force, eddy currents, self-induction, mutual induction, and AC generators."}
                ]
            },
            {
                "name": "Chemistry",
                "code": "CHM12",
                "chapters": [
                    {"number": "1", "title": "Solutions", "content": "Concentration of solutions, solubility, Raoult's law, ideal/non-ideal solutions, colligative properties, elevation of boiling point, and osmotic pressure."},
                    {"number": "2", "title": "Electrochemistry", "content": "Galvanic cells, Nernst equation, conductance in electrolytic solutions, Kohlrausch's law, electrolysis laws, fuel cells, and corrosion kinetics."},
                    {"number": "3", "title": "Chemical Kinetics", "content": "Rate of reaction, factors affecting rate, order and molecularity, integrated rate equations, half-life, collision theory, and activation energy."},
                    {"number": "4", "title": "d- and f-Block Elements", "content": "Transition elements configuration, ionic radii, oxidation states, catalytic properties, interstitial compounds, lanthanoids, and actinoids chemistry."},
                    {"number": "5", "title": "Coordination Compounds", "content": "Werner's theory, ligands, coordination number, IUPAC nomenclature, isomerism, Valence Bond Theory (VBT), and Crystal Field Theory (CFT)."}
                ]
            },
            {
                "name": "Biology",
                "code": "BIO12",
                "chapters": [
                    {"number": "1", "title": "Sexual Reproduction in Flowering Plants", "content": "Flower structure, microsporogenesis, megasporogenesis, pollination types, double fertilization, endosperm and embryo development, and apomixis/polyembryony."},
                    {"number": "2", "title": "Human Reproduction", "content": "Male and female reproductive systems, microscopic anatomy of testis/ovary, gametogenesis, menstrual cycle, fertilization, implantation, pregnancy, and lactation."},
                    {"number": "3", "title": "Principles of Inheritance and Variation", "content": "Mendelian inheritance, devations (incomplete dominance, co-dominance), chromosomal theory of inheritance, sex determination, and genetic disorders."},
                    {"number": "4", "title": "Molecular Basis of Inheritance", "content": "DNA as genetic material structure, packaging, replication, transcription, genetic code, translation, regulation of gene expression, and DNA fingerprinting."},
                    {"number": "5", "title": "Biotechnology: Principles and Processes", "content": "Recombinant DNA technology tools (restriction enzymes, polymerase, ligase, vectors), host organism transformation, and downstream processing steps."}
                ]
            },
            {
                "name": "Mathematics",
                "code": "MATH12",
                "chapters": [
                    {"number": "1", "title": "Relations and Functions", "content": "Types of relations (reflexive, symmetric, transitive, equivalence), one-one and onto functions, and composite functions."},
                    {"number": "2", "title": "Matrices", "content": "Concept, notation, order, types, equality, operations (addition, scalar multiplication, matrix multiplication), transpose, and symmetric matrices."},
                    {"number": "3", "title": "Determinants", "content": "Determinant of square matrix up to 3x3, properties of determinants, minors, cofactors, adjoint, inverse of matrix, and solving linear equations."},
                    {"number": "4", "title": "Integrals", "content": "Integration as inverse process of differentiation, substitution, integration by parts, partial fractions, and Definite Integrals evaluation."},
                    {"number": "5", "title": "Vector Algebra", "content": "Vectors and scalars, magnitude, direction, position vector, components of vector, scalar (dot) product, and vector (cross) product of vectors."}
                ]
            }
        ]
    }
]

def seed_ncert_data(db: Session):
    print("NCERT SEEDER: Starting database seeding of Grade 1-12 NCERT Syllabus...", flush=True)
    for class_data in NCERT_SYLLABUS:
        # Check if class with same name already exists
        cls = db.query(Class).filter(Class.name == class_data["class_name"]).first()
        if not cls:
            cls = Class(
                name=class_data["class_name"],
                grade=class_data["grade"],
                section=class_data["section"]
            )
            db.add(cls)
            db.commit()
            db.refresh(cls)
            print(f"NCERT SEEDER: Created class {cls.name} (ID: {cls.id})", flush=True)
        else:
            print(f"NCERT SEEDER: Class {cls.name} already exists (ID: {cls.id})", flush=True)

        for subj_data in class_data["subjects"]:
            # Check if subject with same code already exists for this class
            subj = db.query(Subject).filter(Subject.code == subj_data["code"], Subject.class_id == cls.id).first()
            if not subj:
                # Also check if code is globally unique (just in case)
                global_subj = db.query(Subject).filter(Subject.code == subj_data["code"]).first()
                if global_subj:
                    print(f"  NCERT SEEDER: Subject with code {subj_data['code']} already exists globally. Linking to class {cls.name}...", flush=True)
                    subj = global_subj
                else:
                    subj = Subject(
                        name=subj_data["name"],
                        code=subj_data["code"],
                        class_id=cls.id,
                        status="Active"
                    )
                    db.add(subj)
                    db.commit()
                    db.refresh(subj)
                    print(f"  NCERT SEEDER: Created subject {subj.name} (Code: {subj.code}, ID: {subj.id})", flush=True)
            else:
                print(f"  NCERT SEEDER: Subject {subj.name} already exists (Code: {subj.code}, ID: {subj.id})", flush=True)

            for chap_data in subj_data["chapters"]:
                # Check if chapter with same title or number already exists for this subject
                chap = db.query(Chapter).filter(
                    Chapter.subject_id == subj.id,
                    (Chapter.title == chap_data["title"]) | (Chapter.number == chap_data["number"])
                ).first()
                if not chap:
                    chap = Chapter(
                        number=chap_data["number"],
                        title=chap_data["title"],
                        subject_id=subj.id,
                        content=chap_data["content"]
                    )
                    db.add(chap)
                    print(f"    NCERT SEEDER: Added chapter {chap.number}: {chap.title}", flush=True)
            
            db.commit()

    print("NCERT SEEDER: Seeding complete!", flush=True)
