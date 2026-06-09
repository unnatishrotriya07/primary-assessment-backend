from sqlalchemy.orm import Session
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter

NCERT_SYLLABUS = [
    # === GRADE 1 ===
    {
        "class_name": "Grade 1",
        "grade": "1",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH1",
                "chapters": [
                    {"number": "1", "title": "Shapes and Space", "content": "Spatial vocabulary (inside-outside, near-far, top-bottom) and basic 3D shapes."},
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
            },
            {
                "name": "Hindi",
                "code": "HIN1",
                "chapters": [
                    {"number": "1", "title": "Chanda Mama", "content": "Introductory poem to Hindi phonetics and simple rhyming structures."},
                    {"number": "2", "title": "Aam ki Kahani", "content": "A picture-based story focusing on vocabulary building and observation skills."},
                    {"number": "3", "title": "Aam ki Tokri", "content": "A simple rhythmic poem about village trade and daily activities."},
                    {"number": "4", "title": "Patte hi Patte", "content": "Understanding natural structures, leaves, shapes, and colors through vocabulary."},
                    {"number": "5", "title": "Pakodi", "content": "A sensory-themed poem about food, smells, and sounds in the kitchen."}
                ]
            }
        ]
    },

    # === GRADE 2 ===
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
                    {"number": "2", "title": "Haldi's Adventure", "content": "A girl meets a talking giraffe named Smiley on her way to school."},
                    {"number": "3", "title": "I am Lucky", "content": "A poem expressing gratitude for being oneself and appreciating animal traits."},
                    {"number": "4", "title": "I Want", "content": "A little monkey wants to be strong like other animals and gets help from a wise woman."},
                    {"number": "5", "title": "A Smile", "content": "A poem about how a smile is a funny thing that spreads happiness all around."},
                    {"number": "6", "title": "The Wind and the Sun", "content": "A contest between the wind and the sun to see who can make a traveler take off his coat."},
                    {"number": "7", "title": "Rain", "content": "A simple poem about rain falling all around on umbrellas, trees, and ships at sea."},
                    {"number": "8", "title": "Storm in the Garden", "content": "Sunu-Sunu the snail visits his friends the ants during a storm and stays safe."},
                    {"number": "9", "title": "Mr. Nobody", "content": "A funny poem about a quiet little man who does all the mischief in everyone's house."},
                    {"number": "10", "title": "Curlylocks and the Three Bears", "content": "A girl enters the cottage of a bear family and tries their porridge, chairs, and beds."}
                ]
            },
            {
                "name": "Hindi",
                "code": "HIN2",
                "chapters": [
                    {"number": "1", "title": "Prarthana", "content": "A devotional poem on moral values, family, and gratefulness."},
                    {"number": "2", "title": "Mera Bharat", "content": "Introduction to the culture, national symbols, and geography of India."},
                    {"number": "3", "title": "Titli aur Kali", "content": "A playful poem showing relations between a butterfly and a flower bud."},
                    {"number": "4", "title": "Bulbul", "content": "Identifying birds, understanding their calls, nested habitats, and behaviors."},
                    {"number": "5", "title": "Khel Khel Mein", "content": "Encouraging physical activities, sportsmanship, and teamwork through games."}
                ]
            }
        ]
    },

    # === GRADE 3 ===
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
                    {"number": "7", "title": "Time Goes On...", "content": "Reading calendars, measuring durations, birth certificates, and clocks."},
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
                "name": "English",
                "code": "ENG3",
                "chapters": [
                    {"number": "1", "title": "Santoor Intro", "content": "A story introducing musical instruments, rhythms, and basic phonics."},
                    {"number": "2", "title": "Good Morning", "content": "A lovely morning poem welcoming birds, trees, sky, and sunshine."},
                    {"number": "3", "title": "The Magic Garden", "content": "A story about a garden run by fairies and children in a school yard."},
                    {"number": "4", "title": "Bird Talk", "content": "Two birds talking about humans, how they grow, walk, and sit on wires."},
                    {"number": "5", "title": "Nina and the Baby Sparrows", "content": "A girl cares for baby sparrows left in her bedroom during a family wedding."},
                    {"number": "6", "title": "The Balloon Man", "content": "A poem describing a man who sells colorful balloons in the market square."},
                    {"number": "7", "title": "The Yellow Butterfly", "content": "A boy chases a beautiful yellow butterfly around his garden, freeing it from a web."}
                ]
            },
            {
                "name": "Environmental Studies",
                "code": "EVS3",
                "chapters": [
                    {"number": "1", "title": "Poonam's Day out", "content": "Observing animals in local surroundings, classifying them by movement/habitat."},
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
            },
            {
                "name": "Hindi",
                "code": "HIN3",
                "chapters": [
                    {"number": "1", "title": "Kakku", "content": "A poem about a boy named Kakku who gets angry quickly and doesn't laugh."},
                    {"number": "2", "title": "Shekhibaz Makkhi", "content": "A story about a proud fly, an angry lion, and a clever spider."},
                    {"number": "3", "title": "Chand wali Amma", "content": "A fantasy story about an old woman sweeping and flying up to the moon."},
                    {"number": "4", "title": "Man Karta Hai", "content": "An imaginative poem about a child wishing to fly, shine, or chirp like birds."},
                    {"number": "5", "title": "Bahadur Bitto", "content": "A story from Punjab about a brave woman Bitto who saves her family's cow from a lion."}
                ]
            }
        ]
    },

    # === GRADE 4 ===
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
                    {"number": "2", "title": "Long and Short", "content": "Measuring distances, converting units (km to m, m to cm), and tracking running records."},
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
                "name": "English",
                "code": "ENG4",
                "chapters": [
                    {"number": "1", "title": "Wake Up!", "content": "A poem encouraging children to wake up early and enjoy nature's morning sounds."},
                    {"number": "2", "title": "Neha's Alarm Clock", "content": "A story about a girl who dislikes waking up early and her relationship with clocks."},
                    {"number": "3", "title": "Noses", "content": "A funny poem about looking at one's nose in the mirror and its unique shape."},
                    {"number": "4", "title": "The Little Fir Tree", "content": "A sad fir tree receives wishes from a magician but learns that original features are best."},
                    {"number": "5", "title": "Run!", "content": "A high-energy poem encouraging children to run into the countryside and be active."},
                    {"number": "6", "title": "Nasruddin's Aim", "content": "Nasruddin boasts about his archery skills and tries to defend his poor shots."}
                ]
            },
            {
                "name": "Environmental Studies",
                "code": "EVS4",
                "chapters": [
                    {"number": "1", "title": "Going to School", "content": "Different transport methods children use to reach school (bamboo bridges, camel cart)."},
                    {"number": "2", "title": "Ear to Ear", "content": "Animal ears, skin patterns, and classifications of birds, mammals, and reptiles."},
                    {"number": "3", "title": "A Day with Nandu", "content": "Elephants' lives, herd dynamics, food habits, and behaviors of baby elephants."},
                    {"number": "4", "title": "The Story of Amrita", "content": "Environmental conservation, Khejadi trees, and the history of the Bishnoi village sacrifice."},
                    {"number": "5", "title": "Anita and the Honeybees", "content": "Beekeeping, life cycle of bees, and a girl's journey to pursue higher education."},
                    {"number": "6", "title": "Omana's Journey", "content": "Train travel, planning, packing, railway stations, and writing travel logs."},
                    {"number": "7", "title": "From the Window", "content": "Changing landscapes, bridges, tunnels, and states of India (Goa to Kerala)."},
                    {"number": "8", "title": "Reaching Grandmother's House", "content": "Different local transports in Kerala (ferries, buses), and reading tickets."},
                    {"number": "9", "title": "Changing Families", "content": "Births, marriages, job transfers, and how they impact family structures and roles."},
                    {"number": "10", "title": "Hu Tu Tu, Hu Tu Tu", "content": "Rules and sportsmanship through Kabaddi, and the stories of sports women."}
                ]
            },
            {
                "name": "Hindi",
                "code": "HIN4",
                "chapters": [
                    {"number": "1", "title": "Man ke Bhole Bhale Badal", "content": "A colorful poem describing the shapes and behaviors of rain clouds."},
                    {"number": "2", "title": "Jaisa Sawal Waisa Jawab", "content": "A court wit story about Birbal answering tricky questions from Khwaja Sara."},
                    {"number": "3", "title": "Kirmiji ki Gend", "content": "A story about kids finding a new ball in summer and arguing over ownership."},
                    {"number": "4", "title": "Papa Jab Bachhe The", "content": "A funny autobiographical narrative about a father's childhood career ambitions."},
                    {"number": "5", "title": "Dost ki Poshak", "content": "A humorous tale about Naseeruddin sharing his fancy clothes with his friend."}
                ]
            }
        ]
    },

    # === GRADE 5 ===
    {
        "class_name": "Grade 5",
        "grade": "5",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH5",
                "chapters": [
                    {"number": "1", "title": "The Fish Tale", "content": "Introduction to large numbers, word problems involving boats and cooperative banks."},
                    {"number": "2", "title": "Shapes and Angles", "content": "Right angles, acute angles, obtuse angles, angles in names, clocks."},
                    {"number": "3", "title": "How Many Squares?", "content": "Grid structure calculation, area of rectangles and triangles, perimeter."},
                    {"number": "4", "title": "Parts and Wholes", "content": "Fractions, numerator/denominator, equivalent fractions, flags patterns."},
                    {"number": "5", "title": "Does it Look the Same?", "content": "Reflection symmetry, mirror lines, rotational symmetry (half-turn, quarter-turn)."},
                    {"number": "6", "title": "Be My Multiple, I'll be Your Factor", "content": "Multiples, common multiples, factors, common factors, and factor trees."},
                    {"number": "7", "title": "Can You See the Pattern?", "content": "Numeric patterns, magic squares, palindrome numbers, and calendar tricks."},
                    {"number": "8", "title": "Mapping Your Way", "content": "Map reading, scales, routes, directions, and perspective views."},
                    {"number": "9", "title": "Boxes and Sketches", "content": "Net drawings of 3D shapes, drawing cubes, and house layout plans."},
                    {"number": "10", "title": "Tenths and Hundredths", "content": "Decimals, place value, converting cm to mm, and measuring small objects."}
                ]
            },
            {
                "name": "English",
                "code": "ENG5",
                "chapters": [
                    {"number": "1", "title": "Ice-cream Man", "content": "A hot-summer poem about the ice-cream man bringing joy with his cart."},
                    {"number": "2", "title": "Wonderful Waste!", "content": "A clever cook in Kerala invents the dish Avial using scrap vegetable bits."},
                    {"number": "3", "title": "Flying Together", "content": "A wise old wild goose warns others about a vine, saving them from a hunter."},
                    {"number": "4", "title": "Crying", "content": "A brief poem about crying and letting all emotions out to find happiness."},
                    {"number": "5", "title": "My Shadow", "content": "A classic poem about a child's shadow that changes size and sleeps late."},
                    {"number": "6", "title": "Robinson Crusoe", "content": "Robinson Crusoe discovers a single human footprint on the sand of a lonely island."}
                ]
            },
            {
                "name": "Environmental Studies",
                "code": "EVS5",
                "chapters": [
                    {"number": "1", "title": "Super Senses", "content": "Animal senses (sight, smell, hearing), tiger behavior, and poaching threats."},
                    {"number": "2", "title": "A Snake Charmer's Story", "content": "Life and culture of Kalbelia snake charmers, traditional medicine, and welfare laws."},
                    {"number": "3", "title": "From Tasting to Digesting", "content": "Tongue taste buds, digestion process, balanced diet, and starvation."},
                    {"number": "4", "title": "Mangoes Round the Year", "content": "Food preservation methods (pickling, drying), and making Mamidi Tandra."},
                    {"number": "5", "title": "Seeds and Seeds", "content": "Seed structure, germination requirements, seed dispersal, pitcher plants."},
                    {"number": "6", "title": "Every Drop Counts", "content": "Water management history, stepwells (baolis), and rainwater harvesting."},
                    {"number": "7", "title": "Experiments with Water", "content": "Floating and sinking, solubility of substances, and the Dead Sea properties."},
                    {"number": "8", "title": "A Treat for Mosquitoes", "content": "Malaria symptoms, lifecycle of mosquitoes, anemia, and Ronald Ross's discovery."},
                    {"number": "9", "title": "Up You Go!", "content": "Mountaineering camp leadership, rock climbing, and Bachhendri Pal's achievements."},
                    {"number": "10", "title": "Walls Tell Stories", "content": "Golconda Fort history, old water wheel mechanisms, weapons, and museum study."}
                ]
            },
            {
                "name": "Hindi",
                "code": "HIN5",
                "chapters": [
                    {"number": "1", "title": "Rakh ki Rassi", "content": "A folk tale from Tibet about a clever daughter-in-law who weaves a rope of ash."},
                    {"number": "2", "title": "Faslon ke Tyohar", "content": "Celebrating harvest festivals in different states of India (Pongal, Makar Sankranti)."},
                    {"number": "3", "title": "Khilonewala", "content": "A child's perspective on buying toy swords and bows to be like Lord Rama."},
                    {"number": "4", "title": "Nanha Fankar", "content": "A 10-year-old stone carver named Keshav meets Emperor Akbar in Fatehpur Sikri."},
                    {"number": "5", "title": "Jahan Chah Wahan Rah", "content": "The inspiring story of Ila, a girl who carves beautiful embroidery using her feet."}
                ]
            }
        ]
    },

    # === GRADE 6 ===
    {
        "class_name": "Grade 6",
        "grade": "6",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH6",
                "chapters": [
                    {"number": "1", "title": "Knowing Our Numbers", "content": "Exploring large numbers up to crores, estimation, commas, brackets, and Roman numerals."},
                    {"number": "2", "title": "Whole Numbers", "content": "Natural vs whole numbers, predecessors, successors, number lines, and properties."},
                    {"number": "3", "title": "Playing with Numbers", "content": "Factors, multiples, prime/composite, divisibility tests, HCF and LCM."},
                    {"number": "4", "title": "Basic Geometrical Ideas", "content": "Introduction to points, lines, segments, rays, curves, polygons, angles, and circles."},
                    {"number": "5", "title": "Understanding Elementary Shapes", "content": "Measuring segments, angles, perpendicular lines, triangles, and 3D shapes."},
                    {"number": "6", "title": "Integers", "content": "Concept of negative numbers, representation on number lines, and basic operations."},
                    {"number": "7", "title": "Fractions", "content": "Proper/improper/mixed fractions, equivalent fractions, simplest form, and comparisons."},
                    {"number": "8", "title": "Decimals", "content": "Converting fractions to decimals, place values, tenths/hundredths, and addition/subtraction."},
                    {"number": "9", "title": "Data Handling", "content": "Tally marks, pictographs, bar graphs, and basic data organization."},
                    {"number": "10", "title": "Mensuration", "content": "Calculating perimeters and areas of regular closed figures (squares, rectangles)."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI6",
                "chapters": [
                    {"number": "1", "title": "Components of Food", "content": "Nutrients (carbohydrates, fats, proteins, vitamins), balanced diet, and deficiency diseases."},
                    {"number": "2", "title": "Sorting Materials into Groups", "content": "Classifying materials based on appearance, hardness, solubility, floatation, and transparency."},
                    {"number": "3", "title": "Separation of Substances", "content": "Sieving, winnowing, handpicking, sedimentation, decantation, filtration, and evaporation."},
                    {"number": "4", "title": "Getting to Know Plants", "content": "Classification of herbs, shrubs, trees. Structures of stems, leaves, roots, and flowers."},
                    {"number": "5", "title": "Body Movements", "content": "Human skeleton, joints (ball-and-socket, hinge, pivotal), cartilage, and animal locomotion."},
                    {"number": "6", "title": "The Living Organisms and Their Surroundings", "content": "Adaptations in deserts, mountains, grasslands, and marine habitats. Biotic vs abiotic components."},
                    {"number": "7", "title": "Motion and Measurement of Distances", "content": "Standard units of measurement, types of motion (rectilinear, circular, periodic)."},
                    {"number": "8", "title": "Light, Shadows and Reflections", "content": "Luminous/non-luminous objects, transparent/translucent/opaque materials, pinhole camera."},
                    {"number": "9", "title": "Electricity and Circuits", "content": "Electric cell, bulb, switches, closed circuits, conductors, and insulators."},
                    {"number": "10", "title": "Fun with Magnets", "content": "Magnetic vs non-magnetic materials, poles, magnetic compass, and demagnetization."}
                ]
            },
            {
                "name": "Social Science",
                "code": "SST6",
                "chapters": [
                    {"number": "1", "title": "What, Where, How and When?", "content": "Historical timelines, archaeological sources, manuscripts, inscriptions, and naming lands."},
                    {"number": "2", "title": "From Gathering to Growing Food", "content": "Mesolithic age, domestication of animals, early farming, and archaeological sites (Mehrgarh)."},
                    {"number": "3", "title": "In the Earliest Cities", "content": "Harappan civilization layout, drainage systems, craft production, trade, and decline theories."},
                    {"number": "4", "title": "What Books and Burials Tell Us", "content": "Rigveda hymns, social classifications, megalithic burials, and study of skeletal remains."},
                    {"number": "5", "title": "Kingdoms, Kings and Republics", "content": "Rajas, ashvamedha sacrifices, Janapadas, Mahajanapadas, taxation, and Mahavira/Buddha's era."},
                    {"number": "6", "title": "The Earth in the Solar System", "content": "Stars, constellations, planets, solar system members, moon phases, asteroids, and meteoroids."},
                    {"number": "7", "title": "Globe: Latitudes and Longitudes", "content": "Equator, prime meridian, heat zones of the Earth, standard time, and longitude offsets."},
                    {"number": "8", "title": "Motions of the Earth", "content": "Earth rotation, revolution, leap year, summer/winter solstices, and spring/autumn equinoxes."},
                    {"number": "9", "title": "What is Government?", "content": "Definition of government, levels of administration, laws, democratic vs monarchical rules."},
                    {"number": "10", "title": "Panchayati Raj", "content": "Gram Sabha, Gram Panchayat, levels of local rural government, and source of funds."}
                ]
            },
            {
                "name": "English",
                "code": "ENG6",
                "chapters": [
                    {"number": "1", "title": "Who Did Patrick's Homework?", "content": "Patrick dislikes homework, but saves an elf who promises to do it for him."},
                    {"number": "2", "title": "How the Dog Found a New Master!", "content": "A dog searches for the strongest master on Earth, finally choosing humans."},
                    {"number": "3", "title": "Taro's Reward", "content": "A thoughtful woodcutter son Taro finds a magical sake waterfall for his parents."},
                    {"number": "4", "title": "Kalpana Chawla in Space", "content": "A tribute to Kalpana Chawla, the first Indian-American astronaut in space."},
                    {"number": "5", "title": "A Different Kind of School", "content": "A visit to Miss Beam's school where kids learn empathy by acting blind/deaf/lame."}
                ]
            }
        ]
    },

    # === GRADE 7 ===
    {
        "class_name": "Grade 7",
        "grade": "7",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH7",
                "chapters": [
                    {"number": "1", "title": "Integers", "content": "Properties of addition, subtraction, multiplication, and division of integers, BODMAS."},
                    {"number": "2", "title": "Fractions and Decimals", "content": "Multiplication and division of fractions and decimals, reciprocal, word problems."},
                    {"number": "3", "title": "Data Handling", "content": "Arithmetic mean, median, mode of ungrouped data, range, bar graphs, probability."},
                    {"number": "4", "title": "Simple Equations", "content": "Setting up equations, solving using balancing and transposition, word problems."},
                    {"number": "5", "title": "Lines and Angles", "content": "Complementary, supplementary, adjacent, linear pairs, parallel lines, transversals."},
                    {"number": "6", "title": "The Triangle and its Properties", "content": "Median, altitude, exterior angle property, angle sum property, Pythagoras theorem."},
                    {"number": "7", "title": "Comparing Quantities", "content": "Ratios, percentages, profit and loss, simple interest calculations."},
                    {"number": "8", "title": "Rational Numbers", "content": "Representation on number line, standard form, comparison, and four operations."},
                    {"number": "9", "title": "Perimeter and Area", "content": "Circumference/area of circles, area of parallelograms and triangles."},
                    {"number": "10", "title": "Algebraic Expressions", "content": "Terms, coefficients, variables, like/unlike terms, addition, subtraction, and formulas."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI7",
                "chapters": [
                    {"number": "1", "title": "Nutrition in Plants", "content": "Autotrophic nutrition, photosynthesis, saprotrophs, parasitic plants, symbiotic relation."},
                    {"number": "2", "title": "Nutrition in Animals", "content": "Human digestive system, steps of nutrition, grass-eaters digestion, Amoeba feeding."},
                    {"number": "3", "title": "Heat", "content": "Clinical vs lab thermometers, conduction, convection, radiation, land/sea breezes."},
                    {"number": "4", "title": "Acids, Bases and Salts", "content": "Organic/mineral acids, strong/weak bases, indicators (litmus, turmeric), neutralization."},
                    {"number": "5", "title": "Physical and Chemical Changes", "content": "Reversible physical changes, chemical reactions, rusting of iron, crystallization."},
                    {"number": "6", "title": "Respiration in Organisms", "content": "Aerobic/anaerobic respiration, human breathing mechanism, respiration in insects/fish."},
                    {"number": "7", "title": "Transportation in Animals and Plants", "content": "Human circulatory system, blood cells, heart structure, excretion, xylem and phloem."},
                    {"number": "8", "title": "Reproduction in Plants", "content": "Asexual (budding, fragmentation), pollination (self/cross), fertilization, seed dispersal."},
                    {"number": "9", "title": "Motion and Time", "content": "Speed, uniform/non-uniform motion, simple pendulum time period, distance-time graphs."},
                    {"number": "10", "title": "Electric Current and its Effects", "content": "Circuit diagrams, heating effect (fuses, heaters), magnetic effect (electromagnets)."}
                ]
            },
            {
                "name": "Social Science",
                "code": "SST7",
                "chapters": [
                    {"number": "1", "title": "Tracing Changes through a Thousand Years", "content": "Comparing maps, cartography changes, new social and political groups, and historical periods."},
                    {"number": "2", "title": "Kings and Kingdoms", "content": "Emergence of new dynasties (Rashtrakutas, Cholas), land grants, and Chola administration."},
                    {"number": "3", "title": "Delhi: 12th to 15th Century", "content": "Tomaras, Chauhans, Delhi Sultanate dynasties (Mamluks, Khaljis, Tughlaqs), and administration."},
                    {"number": "4", "title": "The Mughals (16th to 17th Century)", "content": "Mughal military campaigns, mansabdars, jagirdars, zabt, and Akbar's policies (Sulh-i-kul)."},
                    {"number": "5", "title": "Environment", "content": "Natural vs human-made environment, ecosystems, lithosphere, hydrosphere, and biosphere."},
                    {"number": "6", "title": "Inside Our Earth", "content": "Earth's interior layers (crust, mantle, core), rock cycle, igneous, sedimentary, metamorphic rocks."},
                    {"number": "7", "title": "Our Changing Earth", "content": "Lithospheric plates, endogenic/exogenic forces, earthquakes, volcanoes, and river landforms."},
                    {"number": "8", "title": "On Equality", "content": "Universal Adult Suffrage, equality in Indian democracy, civil rights movements, and Midday Meal."},
                    {"number": "9", "title": "Role of the Government in Health", "content": "Public vs private healthcare services, equal access to health, and Kerala health budget case."},
                    {"number": "10", "title": "How the State Government Works", "content": "MLAs, constituencies, legislative assembly debates, executive decisions, and press conferences."}
                ]
            },
            {
                "name": "English",
                "code": "ENG7",
                "chapters": [
                    {"number": "1", "title": "Three Questions", "content": "A king seeks answers to three questions: the right time, people, and work."},
                    {"number": "2", "title": "A Gift of Chappals", "content": "Children in a South Indian household secretly donate slippers to a poor music master."},
                    {"number": "3", "title": "Gopal and the Hilsa Fish", "content": "A witty courtier Gopal takes up a challenge to bring a Hilsa fish without any questions asked."},
                    {"number": "4", "title": "The Ashes That Made Trees Bloom", "content": "An honest couple's dog guides them to fortune, punishing their greedy neighbors."},
                    {"number": "5", "title": "Quality", "content": "A classic story about the dedication and tragic art of an old bootmaker, Mr. Gessler."}
                ]
            }
        ]
    },

    # === GRADE 8 ===
    {
        "class_name": "Grade 8",
        "grade": "8",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH8",
                "chapters": [
                    {"number": "1", "title": "Rational Numbers", "content": "Properties of rational numbers (closure, associativity, distributivity), identities and inverse."},
                    {"number": "2", "title": "Linear Equations in One Variable", "content": "Solving equations with linear expressions on one/both sides, word problems."},
                    {"number": "3", "title": "Understanding Quadrilaterals", "content": "Polygons, angle sum property, exterior angles, types of quadrilaterals (parallelogram)."},
                    {"number": "4", "title": "Data Handling", "content": "Frequency distributions, histograms, pie charts, and basic probability concepts."},
                    {"number": "5", "title": "Squares and Square Roots", "content": "Properties of square numbers, finding square roots through prime factorization, division."},
                    {"number": "6", "title": "Cubes and Cube Roots", "content": "Properties of cube numbers, finding cube roots, and estimation methods."},
                    {"number": "7", "title": "Comparing Quantities", "content": "Compound interest formulas, tax, discounts, profit/loss percentage, appreciation."},
                    {"number": "8", "title": "Algebraic Expressions and Identities", "content": "Monomials, binomials, polynomials, multiplication of expressions, standard identities."},
                    {"number": "9", "title": "Mensuration", "content": "Area of trapezium, polygon, surface area and volume of cube, cuboid, cylinder."},
                    {"number": "10", "title": "Exponents and Powers", "content": "Negative exponents laws, scientific notation for very small/large numbers."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI8",
                "chapters": [
                    {"number": "1", "title": "Crop Production and Management", "content": "Agricultural practices, sowing, irrigation, harvesting, manure vs fertilizers."},
                    {"number": "2", "title": "Microorganisms: Friend and Foe", "content": "Bacteria, fungi, protozoa, viruses. Vaccinations, food preservation, nitrogen cycle."},
                    {"number": "3", "title": "Coal and Petroleum", "content": "Fossil fuels, fractional distillation of petroleum, coal tar, gas conservation."},
                    {"number": "4", "title": "Combustion and Flame", "content": "Combustion conditions, ignition temperature, fire control, candle flame zones."},
                    {"number": "5", "title": "Conservation of Plants and Animals", "content": "Deforestation impacts, sanctuaries, national parks, Red Data Book, reforestation."},
                    {"number": "6", "title": "Cell—Structure and Functions", "content": "Discovery of cell, organelles (nucleus, cytoplasm, cell wall, chloroplasts)."},
                    {"number": "7", "title": "Reproduction in Animals", "content": "Sexual vs asexual reproduction, fertilization (internal/external), cloning (Dolly)."},
                    {"number": "8", "title": "Reaching the Age of Adolescence", "content": "Puberty changes, hormones (endocrine glands), sex determination, health."},
                    {"number": "9", "title": "Force and Pressure", "content": "Contact vs non-contact forces, atmospheric pressure, liquid pressure measurements."},
                    {"number": "10", "title": "Friction", "content": "Static vs sliding friction, factors affecting friction, advantages and disadvantages."}
                ]
            },
            {
                "name": "Social Science",
                "code": "SST8",
                "chapters": [
                    {"number": "1", "title": "How, When and Where", "content": "Importance of dates, periodization of Indian history (Hindu, Muslim, British), colonial survey."},
                    {"number": "2", "title": "From Trade to Territory", "content": "East India Company arrival, Battle of Plassey/Buxar, Subsidiary Alliance, Doctrine of Lapse."},
                    {"number": "3", "title": "Ruling the Countryside", "content": "Permanent Settlement, Mahalwari and Ryotwari systems, demand for Indian indigo, Rebellion."},
                    {"number": "4", "title": "Tribals, Dikus and the Vision of a Golden Age", "content": "Tribal lifestyles (shifting cultivators, hunters), impact of British forest laws, Birsa Munda."},
                    {"number": "5", "title": "When People Rebel", "content": "1857 Revolt causes (sepoys, zamindars, queens), key leaders (Mangal Pandey), and aftermath."},
                    {"number": "6", "title": "Resources", "content": "Definition, types (natural, human-made, human), utility, value, and sustainable development."},
                    {"number": "7", "title": "Land, Soil, Water, Natural Vegetation", "content": "Land use, soil formation, weathering, soil conservation, water scarcity, and forest types."},
                    {"number": "8", "title": "The Indian Constitution", "content": "Key features of Indian Constitution, federalism, parliamentary form, separation of powers."},
                    {"number": "9", "title": "Understanding Secularism", "content": "Separation of religion from state, Indian secularism vs western models, minority protections."},
                    {"number": "10", "title": "Why Do We Need a Parliament?", "content": "Role of citizens, selection of national government, control of executive, and bill passing."}
                ]
            },
            {
                "name": "English",
                "code": "ENG8",
                "chapters": [
                    {"number": "1", "title": "The Best Christmas Present in the World", "content": "A story set during WWI about a British soldier's letter found in a desk."},
                    {"number": "2", "title": "The Tsunami", "content": "Real accounts of courage and survival during the 2004 Indian Ocean tsunami."},
                    {"number": "3", "title": "Glimpses of the Past", "content": "Comic strips depicting Indian history from 1757 to 1857 under East India Company."},
                    {"number": "4", "title": "Bepin Choudhury's Lapse of Memory", "content": "A humorous tale of a man tricked into believing he lost memory of a trip to Ranchi."},
                    {"number": "5", "title": "The Summit Within", "content": "Major H.P.S. Ahluwalia writes about his climb to Mount Everest and the mental summits."}
                ]
            }
        ]
    },

    # === GRADE 9 ===
    {
        "class_name": "Grade 9",
        "grade": "9",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH9",
                "chapters": [
                    {"number": "1", "title": "Number Systems", "content": "Irrational numbers, real numbers, decimal expansions, operations, and laws of exponents."},
                    {"number": "2", "title": "Polynomials", "content": "Polynomials in one variable, zeroes, remainder theorem, factorization, algebraic identities."},
                    {"number": "3", "title": "Coordinate Geometry", "content": "Cartesian system, plotting points, quadrant signs, and axes concepts."},
                    {"number": "4", "title": "Linear Equations in Two Variables", "content": "Linear equations, solution representations, graph plotting, and parallel lines equations."},
                    {"number": "5", "title": "Introduction to Euclid's Geometry", "content": "Axioms and postulates, historical context, and equivalent formulations of fifth postulate."},
                    {"number": "6", "title": "Lines and Angles", "content": "Intersecting lines, angle pairs, parallel lines and transversals, angle sum property."},
                    {"number": "7", "title": "Triangles", "content": "Congruence criteria (SAS, ASA, SSS, RHS), inequalities, and properties of triangles."},
                    {"number": "8", "title": "Quadrilaterals", "content": "Properties of parallelograms, mid-point theorem, and angle sum of quadrilaterals."},
                    {"number": "9", "title": "Circles", "content": "Angle subtended by chord, perpendicular from center, equal chords distances, cyclic quadrilaterals."},
                    {"number": "10", "title": "Heron's Formula", "content": "Calculating triangle areas without base/height parameters, application to quadrilaterals."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI9",
                "chapters": [
                    {"number": "1", "title": "Matter in Our Surroundings", "content": "Physical nature, states of matter, temperature/pressure effects, and evaporation."},
                    {"number": "2", "title": "Is Matter Around Us Pure?", "content": "Mixtures, solutions, suspensions, colloids, elements, compounds, physical/chemical changes."},
                    {"number": "3", "title": "Atoms and Molecules", "content": "Chemical combination laws, Dalton's atomic theory, formula writing, mole concept."},
                    {"number": "4", "title": "Structure of the Atom", "content": "Thomson, Rutherford, Bohr models. Valency, atomic/mass numbers, isotopes."},
                    {"number": "5", "title": "The Fundamental Unit of Life", "content": "Cell discovery, plasma membrane, nucleus, organelles (mitochondria, chloroplasts)."},
                    {"number": "6", "title": "Tissues", "content": "Meristematic/permanent plant tissues, animal tissues (epithelial, connective, muscular, nervous)."},
                    {"number": "7", "title": "Motion", "content": "Distance vs displacement, speed, velocity, acceleration equations, uniform circular motion."},
                    {"number": "8", "title": "Force and Laws of Motion", "content": "Balanced/unbalanced forces, inertia, Newton's three laws of motion, momentum."},
                    {"number": "9", "title": "Gravitation", "content": "Universal law of gravitation, free fall, acceleration due to gravity, mass vs weight, thrust."},
                    {"number": "10", "title": "Work and Energy", "content": "Scientific concept of work, potential/kinetic energy, conservation law, power."}
                ]
            },
            {
                "name": "Social Science",
                "code": "SST9",
                "chapters": [
                    {"number": "1", "title": "The French Revolution", "content": "French society, Estates General, storming of Bastille, Jacobins, Reign of Terror, Napoleon."},
                    {"number": "2", "title": "Socialism in Europe and the Russian Revolution", "content": "Liberals, radicals, conservatives. 1905/1917 revolutions, Bolsheviks, and collectivisation."},
                    {"number": "3", "title": "Nazism and the Rise of Hitler", "content": "Weimar Republic fall, Hitler's rise, Nazi ideology, racial state, youth/women in Nazi Germany."},
                    {"number": "4", "title": "India – Size and Location", "content": "Latitudes, longitudes, standard meridian, India's neighbors, strategic location."},
                    {"number": "5", "title": "Physical Features of India", "content": "Himalayas, Northern Plains, Peninsular Plateau, Thar Desert, Coastal Plains, Islands."},
                    {"number": "6", "title": "Drainage", "content": "Himalayan vs Peninsular rivers, river systems (Ganga, Indus), lakes, and economics of water."},
                    {"number": "7", "title": "What Is Democracy? Why Democracy?", "content": "Democratic features (fair elections, rule of law), arguments for and against democracy."},
                    {"number": "8", "title": "Constitutional Design", "content": "South Africa constitution struggle, need for a constitution, Indian Constituent Assembly."},
                    {"number": "9", "title": "The Story of Village Palampur", "content": "Production factors, land distribution, modern farming, non-farming activities."},
                    {"number": "10", "title": "People as Resource", "content": "Human capital formation, education, health systems, types of unemployment."}
                ]
            },
            {
                "name": "English",
                "code": "ENG9",
                "chapters": [
                    {"number": "1", "title": "The Fun They Had", "content": "Set in future, kids find an old book and learn about schoolhouses from the past."},
                    {"number": "2", "title": "The Sound of Music", "content": "Biographies of Evelyn Glennie (deaf percussionist) and Ustad Bismillah Khan (shehnai)."},
                    {"number": "3", "title": "The Little Girl", "content": "Kezia is afraid of her strict father but realizes his love after a nightmare."},
                    {"number": "4", "title": "A Truly Beautiful Mind", "content": "A biography of Albert Einstein, focusing on scientific brilliance and global peace efforts."},
                    {"number": "5", "title": "My Childhood", "content": "APJ Abdul Kalam's memories of his family, friends, and early education in Rameswaram."}
                ]
            }
        ]
    },

    # === GRADE 10 ===
    {
        "class_name": "Grade 10",
        "grade": "10",
        "section": "A",
        "subjects": [
            {
                "name": "Mathematics",
                "code": "MATH10",
                "chapters": [
                    {"number": "1", "title": "Real Numbers", "content": "Fundamental Theorem of Arithmetic, proving irrationality (root 2, 3, 5), decimal expansions."},
                    {"number": "2", "title": "Polynomials", "content": "Geometrical zeroes of a polynomial, relation between coefficients of quadratic polynomials."},
                    {"number": "3", "title": "Pair of Linear Equations in Two Variables", "content": "Graphical method, algebraic methods (substitution, elimination), reducible systems."},
                    {"number": "4", "title": "Quadratic Equations", "content": "Standard form, factorization, quadratic formula, nature of roots, word problems."},
                    {"number": "5", "title": "Arithmetic Progressions", "content": "nth term of an AP, sum of first n terms, common difference, AP applications."},
                    {"number": "6", "title": "Triangles", "content": "Similar figures, Basic Proportionality Theorem, similarity criteria (AAA, SAS, SSS)."},
                    {"number": "7", "title": "Coordinate Geometry", "content": "Distance formula, section formula (internal division), coordinate geometry layouts."},
                    {"number": "8", "title": "Introduction to Trigonometry", "content": "Trigonometric ratios of acute angles, values at standard angles, basic identities."},
                    {"number": "9", "title": "Some Applications of Trigonometry", "content": "Heights and distances problems, angle of elevation, angle of depression."},
                    {"number": "10", "title": "Circles", "content": "Tangents to circles, properties of length of tangents drawn from external points."}
                ]
            },
            {
                "name": "Science",
                "code": "SCI10",
                "chapters": [
                    {"number": "1", "title": "Chemical Reactions and Equations", "content": "Chemical equations balancing, combination, decomposition, displacement, redox reactions."},
                    {"number": "2", "title": "Acids, Bases and Salts", "content": "pH scale, indicators, chemical properties of acids/bases, baking/washing soda, plaster of Paris."},
                    {"number": "3", "title": "Metals and Non-metals", "content": "Metals physical/chemical properties, reactivity series, ionic bonds, metallurgy basics."},
                    {"number": "4", "title": "Carbon and its Compounds", "content": "Covalent bonding in carbon, homologous series, functional groups, saponification."},
                    {"number": "5", "title": "Life Processes", "content": "Autotrophic/heterotrophic nutrition, human respiration, circulation, plant/animal excretion."},
                    {"number": "6", "title": "Control and Coordination", "content": "Human brain, nervous system, reflex action, plant hormones, animal hormones."},
                    {"number": "7", "title": "How do Organisms Reproduce?", "content": "Fission, budding, vegetative propagation, human reproductive systems, birth control."},
                    {"number": "8", "title": "Heredity", "content": "Mendel's laws of inheritance, monohybrid/dihybrid crosses, human sex determination."},
                    {"number": "9", "title": "Light Reflection and Refraction", "content": "Reflection by spherical mirrors, mirror formula, refraction laws, lenses, power."},
                    {"number": "10", "title": "The Human Eye and the Colorful World", "content": "Defects of vision (myopia, hypermetropia), prism refraction, dispersion, atmospheric scattering."}
                ]
            },
            {
                "name": "Social Science",
                "code": "SST10",
                "chapters": [
                    {"number": "1", "title": "The Rise of Nationalism in Europe", "content": "French Revolution, nation-states creation, German/Italian unification, Balkan conflicts."},
                    {"number": "2", "title": "Nationalism in India", "content": "Satyagraha, Non-Cooperation, Civil Disobedience, Quit India, Khilafat, Sense of Belonging."},
                    {"number": "3", "title": "The Making of a Global World", "content": "Pre-modern trade, silk routes, indentured labor, Great Depression, Bretton Woods."},
                    {"number": "4", "title": "The Age of Industrialisation", "content": "Before industrialization, factories rise, steam engines, hand labor, market for goods."},
                    {"number": "5", "title": "Resources and Development", "content": "Resource classification, planning, land degradation, soil types, conservation methods."},
                    {"number": "6", "title": "Water Resources", "content": "Water scarcity, multi-purpose dams, rainwater harvesting, river pollution issues."},
                    {"number": "7", "title": "Agriculture", "content": "Farming types (primitive, commercial), cropping patterns, major crops (rice, wheat, tea)."},
                    {"number": "8", "title": "Power Sharing", "content": "Belgium vs Sri Lanka models, majority rule, federal/coalition systems."},
                    {"number": "9", "title": "Federalism", "content": "Key features of federalism, union/state lists, local government decentralization."},
                    {"number": "10", "title": "Development", "content": "HDI, National Income, per capita income, sustainable growth indicators."}
                ]
            },
            {
                "name": "English",
                "code": "ENG10",
                "chapters": [
                    {"number": "1", "title": "A Letter to God", "content": "Lencho writes a letter to God asking for pesos after a hailstorm ruins his crop."},
                    {"number": "2", "title": "Nelson Mandela: Long Walk to Freedom", "content": "Excerpts from Mandela's autobiography detailing the inauguration of a democratic South India/Africa."},
                    {"number": "3", "title": "Two Stories about Flying", "content": "Stories about a young seagull's first flight and a pilot guided by a black aeroplane."},
                    {"number": "4", "title": "From the Diary of Anne Frank", "content": "Anne's personal diary entries while hiding from Nazis, describing school life."},
                    {"number": "5", "title": "Glimpses of India", "content": "Three stories showcasing Baker from Goa, Coorg landscapes, and Tea from Assam."}
                ]
            }
        ]
    },

    # === GRADE 11 ===
    {
        "class_name": "Grade 11",
        "grade": "11",
        "section": "A",
        "subjects": [
            {
                "name": "Physics",
                "code": "PHY11",
                "chapters": [
                    {"number": "1", "title": "Units and Measurements", "content": "SI units, fundamental/derived, dimensional analysis, significant figures, errors."},
                    {"number": "2", "title": "Motion in a Straight Line", "content": "Displacement, velocity, uniform acceleration, kinematic graphs, equations of motion."},
                    {"number": "3", "title": "Motion in a Plane", "content": "Vectors resolution, addition, projectile motion, uniform circular motion."},
                    {"number": "4", "title": "Laws of Motion", "content": "Newton's laws, momentum conservation, friction, circular motion dynamics."},
                    {"number": "5", "title": "Work, Energy and Power", "content": "Work-energy theorem, potential/kinetic energy, conservative forces, collisions, power."},
                    {"number": "6", "title": "System of Particles and Rotational Motion", "content": "Center of mass, torque, angular momentum, moment of inertia, theorems."},
                    {"number": "7", "title": "Gravitation", "content": "Kepler's laws, universal gravitation, acceleration g, orbital speed, escape velocity."},
                    {"number": "8", "title": "Mechanical Properties of Solids", "content": "Elastic behavior, stress, strain, Hooke's law, Young's modulus, shear modulus."},
                    {"number": "9", "title": "Mechanical Properties of Fluids", "content": "Pascal's law, viscosity, surface tension, Bernoulli's principle, terminal velocity."},
                    {"number": "10", "title": "Thermodynamics", "content": "Thermal equilibrium, Zeroth, First, and Second laws, heat engines, refrigerators."}
                ]
            },
            {
                "name": "Chemistry",
                "code": "CHM11",
                "chapters": [
                    {"number": "1", "title": "Some Basic Concepts of Chemistry", "content": "Mole concept, empirical/molecular formulas, stoichiometry calculations, limiting reagent."},
                    {"number": "2", "title": "Structure of Atom", "content": "Bohr's model, dual nature of matter, Heisenberg uncertainty, quantum numbers."},
                    {"number": "3", "title": "Classification of Elements and Periodicity", "content": "Modern periodic table, s/p/d/f blocks, atomic radii, ionization enthalpy, electronegativity."},
                    {"number": "4", "title": "Chemical Bonding and Molecular Structure", "content": "Lewis structures, VSEPR theory, hybridization (sp, sp2, sp3), molecular orbital theory."},
                    {"number": "5", "title": "Chemical Thermodynamics", "content": "First/second law, enthalpy, Hess's law, entropy, Gibbs energy, spontaneity."},
                    {"number": "6", "title": "Equilibrium", "content": "Law of mass action, Le Chatelier's principle, pH scale, buffer solutions."},
                    {"number": "7", "title": "Redox Reactions", "content": "Oxidation/reduction definitions, oxidation number, balancing redox equations."},
                    {"number": "8", "title": "Organic Chemistry - Principles", "content": "IUPAC nomenclature, isomerism, inductive/electromeric effects, resonance."},
                    {"number": "9", "title": "Hydrocarbons", "content": "Alkanes, alkenes, alkynes preparation, physical properties, chemical reactions."},
                    {"number": "10", "title": "Environmental Chemistry", "content": "Air, water, soil pollution, greenhouse effect, ozone depletion, green chemistry."}
                ]
            },
            {
                "name": "Biology",
                "code": "BIO11",
                "chapters": [
                    {"number": "1", "title": "The Living World", "content": "Living features, binomial nomenclature (Linnaeus), taxonomic hierarchy, aids."},
                    {"number": "2", "title": "Biological Classification", "content": "Five kingdoms (Monera, Protista, Fungi, Plantae, Animalia), viruses, lichens."},
                    {"number": "3", "title": "Plant Kingdom", "content": "Algae, Bryophytes, Pteridophytes, Gymnosperms, Angiosperms alternation of generations."},
                    {"number": "4", "title": "Animal Kingdom", "content": "Symmetry, coelom, chordates vs non-chordates phyla characteristics."},
                    {"number": "5", "title": "Cell: The Unit of Life", "content": "Prokaryotic vs eukaryotic, membrane structure, nucleus, mitochondria, plastids."},
                    {"number": "6", "title": "Biomolecules", "content": "Carbohydrates, proteins, nucleic acids, lipids structure, enzymes action."},
                    {"number": "7", "title": "Cell Cycle and Cell Division", "content": "Stages of cell cycle, Mitosis phases, Meiosis I and II significance."},
                    {"number": "8", "title": "Photosynthesis in Higher Plants", "content": "Light/dark reactions, cyclic/non-cyclic photophosphorylation, C3 and C4 pathways."},
                    {"number": "9", "title": "Respiration in Plants", "content": "Glycolysis, Krebs cycle, electron transport system, respiratory quotient."},
                    {"number": "10", "title": "Chemical Coordination and Integration", "content": "Endocrine glands, hormones mechanism, thyroid, adrenal, pituitary functions."}
                ]
            },
            {
                "name": "Mathematics",
                "code": "MATH11",
                "chapters": [
                    {"number": "1", "title": "Sets", "content": "Set representations, empty/finite sets, subsets, power sets, Venn diagrams, union/intersection."},
                    {"number": "2", "title": "Relations and Functions", "content": "Cartesian product, domain/range of relations, standard functions (modulus, signum)."},
                    {"number": "3", "title": "Trigonometric Functions", "content": "Degrees/radians, identities, trigonometric equations, sine/cosine formulas."},
                    {"number": "4", "title": "Complex Numbers and Quadratic Equations", "content": "Imaginary unit i, algebra of complex numbers, modulus, conjugate, polar representation."},
                    {"number": "5", "title": "Linear Inequalities", "content": "Solving algebraic inequalities in one/two variables, graphical solutions."},
                    {"number": "6", "title": "Permutations and Combinations", "content": "Factorial, nPr and nCr formulas, permutations under constraints, word problems."},
                    {"number": "7", "title": "Binomial Theorem", "content": "Binomial expansion for positive integers, general/middle term calculation."},
                    {"number": "8", "title": "Sequences and Series", "content": "Arithmetic Progression, Geometric Progression, infinite GP sum, special series."},
                    {"number": "9", "title": "Straight Lines", "content": "Slope of line, angle between lines, standard forms (intercept, normal), distance formulas."},
                    {"number": "10", "title": "Limits and Derivatives", "content": "Limit concepts, algebra of limits, derivative definition, rates of change."}
                ]
            },
            {
                "name": "Business Studies",
                "code": "BST11",
                "chapters": [
                    {"number": "1", "title": "Business, Trade and Commerce", "content": "History of commerce in India, concept/characteristics of business, classification of activities."},
                    {"number": "2", "title": "Forms of Business Organisations", "content": "Sole proprietorship, partnership, HUF, cooperative societies, joint stock companies."},
                    {"number": "3", "title": "Private, Public and Global Enterprises", "content": "Departmental undertakings, statutory corporations, government companies, MNCs."},
                    {"number": "4", "title": "Business Services", "content": "Banking services, insurance types, postal/telecom services, warehousing."},
                    {"number": "5", "title": "Emerging Modes of Business", "content": "E-business scope, benefits, security risks, outsourcing (BPO, KPO) concepts."}
                ]
            },
            {
                "name": "Accountancy",
                "code": "ACT11",
                "chapters": [
                    {"number": "1", "title": "Introduction to Accounting", "content": "Accounting definitions, objectives, branch types, double entry system, database."},
                    {"number": "2", "title": "Theory Base of Accounting", "content": "Accounting principles, GAAP, going concern, consistency, accrual, accounting standards."},
                    {"number": "3", "title": "Recording of Transactions - I", "content": "Accounting equation, debit/credit rules, journal, ledger posting, cash book."},
                    {"number": "4", "title": "Recording of Transactions - II", "content": "Purchases book, sales book, purchase return, sales return, journal proper."},
                    {"number": "5", "title": "Bank Reconciliation Statement", "content": "Need for BRS, cash book vs pass book balance difference causes, preparation."}
                ]
            },
            {
                "name": "Economics",
                "code": "ECO11",
                "chapters": [
                    {"number": "1", "title": "Introduction to Statistics", "content": "Meaning and scope of statistics in economics, database resources."},
                    {"number": "2", "title": "Collection, Organisation of Data", "content": "Primary/secondary sources, census vs sample method, frequency tables."},
                    {"number": "3", "title": "Indian Economy on the Eve of Independence", "content": "State of agriculture, industry, foreign trade under British rule."},
                    {"number": "4", "title": "Indian Economy 1950-1990", "content": "Five-year plans objectives, green revolution, industrial licensing policies."},
                    {"number": "5", "title": "LPG Policies", "content": "Liberalisation, Privatisation, and Globalisation policies since 1991."}
                ]
            },
            {
                "name": "English",
                "code": "ENG11",
                "chapters": [
                    {"number": "1", "title": "The Portrait of a Lady", "content": "Author's memories of his grandmother, her lifestyle, religious devotion, and death."},
                    {"number": "2", "title": "We're Not Afraid to Die", "content": "A family's adventurous and life-threatening voyage across the Indian Ocean."},
                    {"number": "3", "title": "Discovering Tut: the Saga Continues", "content": "Archaeological discovery of King Tut's mummy and modern forensic research."},
                    {"number": "4", "title": "The Browning Version", "content": "A school play extract detailing the relationship between Crocker-Harris and Taplow."},
                    {"number": "5", "title": "Silk Road", "content": "The author's travelogue describing the pilgrimage journey to Mount Kailash."}
                ]
            }
        ]
    },

    # === GRADE 12 ===
    {
        "class_name": "Grade 12",
        "grade": "12",
        "section": "A",
        "subjects": [
            {
                "name": "Physics",
                "code": "PHY12",
                "chapters": [
                    {"number": "1", "title": "Electric Charges and Fields", "content": "Coulomb's law, electric field lines, dipole, electric flux, Gauss's law."},
                    {"number": "2", "title": "Electrostatic Potential and Capacitance", "content": "Potential energy, conductors, dielectrics, capacitors, parallel plate capacitor."},
                    {"number": "3", "title": "Current Electricity", "content": "Ohm's law, drift velocity, resistivity, Kirchhoff's rules, Wheatstone bridge, potentiometer."},
                    {"number": "4", "title": "Moving Charges and Magnetism", "content": "Biot-Savart law, Ampere's law, cyclotron, torque on loop, galvanometer."},
                    {"number": "5", "title": "Magnetism and Matter", "content": "Bar magnet, earth's magnetic elements, magnetic properties (dia/para/ferro)."},
                    {"number": "6", "title": "Electromagnetic Induction", "content": "Faraday's laws, Lenz's law, motional EMF, eddy currents, self/mutual induction."},
                    {"number": "7", "title": "Alternating Current", "content": "LCR series circuit, resonance, power factor, transformers, AC generator."},
                    {"number": "8", "title": "Electromagnetic Waves", "content": "Displacement current, EM wave characteristics, EM spectrum uses."},
                    {"number": "9", "title": "Ray Optics and Optical Instruments", "content": "Reflection, refraction, total internal reflection, lenses, prism dispersion, microscopes."},
                    {"number": "10", "title": "Wave Optics", "content": "Huygens principle, interference, Young's double slit, diffraction, polarization."}
                ]
            },
            {
                "name": "Chemistry",
                "code": "CHM12",
                "chapters": [
                    {"number": "1", "title": "Solutions", "content": "Solubility, Raoult's law, ideal/non-ideal solutions, colligative properties, van 't Hoff factor."},
                    {"number": "2", "title": "Electrochemistry", "content": "Galvanic cells, Nernst equation, conductance, Kohlrausch's law, electrolysis, fuel cells."},
                    {"number": "3", "title": "Chemical Kinetics", "content": "Rate of reaction, reaction order/molecularity, half-life, activation energy, Arrhenius equation."},
                    {"number": "4", "title": "d- and f-Block Elements", "content": "Transition elements characteristics, lanthanoids, actinoids contraction, oxidation states."},
                    {"number": "5", "title": "Coordination Compounds", "content": "Ligands, IUPAC nomenclature, isomerism, Valence Bond and Crystal Field theories."},
                    {"number": "6", "title": "Haloalkanes and Haloarenes", "content": "SN1 and SN2 reaction mechanisms, preparation, physical/chemical properties, environmental effects."},
                    {"number": "7", "title": "Alcohols, Phenols and Ethers", "content": "Classification, preparation, dehydration of alcohols, acidity of phenols."},
                    {"number": "8", "title": "Aldehydes, Ketones and Carboxylic Acids", "content": "Nucleophilic addition, oxidation/reduction, acidity of carboxylic acids."},
                    {"number": "9", "title": "Amines", "content": "Basicity of amines, diazotisation, chemical reactions of aniline."},
                    {"number": "10", "title": "Biomolecules", "content": "Carbohydrates (monosaccharides), proteins (amino acids, peptide bond), nucleic acids (DNA/RNA)."}
                ]
            },
            {
                "name": "Biology",
                "code": "BIO12",
                "chapters": [
                    {"number": "1", "title": "Sexual Reproduction in Flowering Plants", "content": "Pollen/ovule development, double fertilization, endosperm, apomixis."},
                    {"number": "2", "title": "Human Reproduction", "content": "Male/female anatomy, gametogenesis, menstrual cycle, fertilization, implantation, lactation."},
                    {"number": "3", "title": "Reproductive Health", "content": "Contraception, STD prevention, IVF/ART technologies, population control."},
                    {"number": "4", "title": "Principles of Inheritance and Variation", "content": "Mendelian genetics, co-dominance, linkage, sex determination, chromosomal disorders."},
                    {"number": "5", "title": "Molecular Basis of Inheritance", "content": "DNA structure, replication, transcription, genetic code, translation, DNA fingerprinting."},
                    {"number": "6", "title": "Evolution", "content": "Origin of life, Darwin's theory, evidence of evolution, Hardy-Weinberg equilibrium."},
                    {"number": "7", "title": "Human Health and Disease", "content": "Malaria, cancer, AIDS, immunity (active/passive), drug/alcohol abuse."},
                    {"number": "8", "title": "Biotechnology: Principles and Processes", "content": "Restriction enzymes, cloning vectors, transformation, downstream processing."},
                    {"number": "9", "title": "Biotechnology and its Applications", "content": "Bt cotton, gene therapy, insulin production, transgenics, bioethics."},
                    {"number": "10", "title": "Ecosystem", "content": "Productivity, decomposition, energy flow (trophic levels), ecological pyramids."}
                ]
            },
            {
                "name": "Mathematics",
                "code": "MATH12",
                "chapters": [
                    {"number": "1", "title": "Relations and Functions", "content": "Reflexive, symmetric, transitive, equivalence relations, one-one/onto functions."},
                    {"number": "2", "title": "Inverse Trigonometric Functions", "content": "Domain, range, principal value branches, graphs, and simple identities."},
                    {"number": "3", "title": "Matrices", "content": "Order, types, operations, matrix multiplication, transpose, symmetric matrices."},
                    {"number": "4", "title": "Determinants", "content": "Determinant evaluation, area of triangle, minors, cofactors, matrix inverse."},
                    {"number": "5", "title": "Continuity and Differentiability", "content": "Limits check, chain rule, implicit differentiation, logarithmic differentiation, Mean Value Theorem."},
                    {"number": "6", "title": "Application of Derivatives", "content": "Rate of change, tangent/normal slope, maxima/minima, increasing/decreasing functions."},
                    {"number": "7", "title": "Integrals", "content": "Indefinite integrals, substitution, partial fractions, parts integration, definite integrals properties."},
                    {"number": "8", "title": "Application of Integrals", "content": "Calculating area under simple curves (lines, parabolas, circles)."},
                    {"number": "9", "title": "Differential Equations", "content": "Order/degree, general/particular solution, homogeneous/linear differential equations."},
                    {"number": "10", "title": "Vector Algebra", "content": "Scalar/vector quantities, direction cosines, dot product, cross product."}
                ]
            },
            {
                "name": "Business Studies",
                "code": "BST12",
                "chapters": [
                    {"number": "1", "title": "Nature and Significance of Management", "content": "Management objectives, levels, functions, coordination features."},
                    {"number": "2", "title": "Principles of Management", "content": "Fayol's principles, Taylor's scientific management techniques."},
                    {"number": "3", "title": "Business Environment", "content": "Dimensions (economic, social, technological), demonetization impact."},
                    {"number": "4", "title": "Planning", "content": "Steps in planning process, single-use vs standing plans."},
                    {"number": "5", "title": "Organising", "content": "Steps, divisional vs functional structure, delegation, decentralization."}
                ]
            },
            {
                "name": "Accountancy",
                "code": "ACT12",
                "chapters": [
                    {"number": "1", "title": "Accounting for Partnership", "content": "Partnership deed, profit/loss appropriation account, capital accounts."},
                    {"number": "2", "title": "Admission of a Partner", "content": "New profit sharing ratio, sacrificing ratio, goodwill treatment, revaluation."},
                    {"number": "3", "title": "Retirement/Death of a Partner", "content": "Gaining ratio computation, executor account preparation, goodwill adjustment."},
                    {"number": "4", "title": "Dissolution of Partnership Firm", "content": "Realisation account, settlement of accounts, cash/bank account closing."},
                    {"number": "5", "title": "Accounting for Share Capital", "content": "Issue of shares, pro-rata allotment, forfeiture, reissue of shares."}
                ]
            },
            {
                "name": "Economics",
                "code": "ECO12",
                "chapters": [
                    {"number": "1", "title": "Introduction to Macroeconomics", "content": "Macro vs micro, circular flow of income (two-sector model)."},
                    {"number": "2", "title": "National Income Accounting", "content": "GDP, GNP, NDP, NNP, value added method, expenditure method, income method."},
                    {"number": "3", "title": "Money and Banking", "content": "Money supply measures, commercial banks credit creation, central bank credit control."},
                    {"number": "4", "title": "Determination of Income and Employment", "content": "Aggregate demand, investment multiplier, excess/deficient demand measures."},
                    {"number": "5", "title": "Government Budget and the Economy", "content": "Budget objectives, components, revenue/capital budget, fiscal/primary deficit."}
                ]
            },
            {
                "name": "English",
                "code": "ENG12",
                "chapters": [
                    {"number": "1", "title": "The Last Lesson", "content": "Franz describes his last French lesson taught by M. Hamel after German decree."},
                    {"number": "2", "title": "Lost Spring", "content": "Stories of stolen childhood, describing children in ragpicking (Saheb) and bangle making (Mukesh)."},
                    {"number": "3", "title": "Deep Water", "content": "William Douglas writes about his childhood fear of water and how he overcame it."},
                    {"number": "4", "title": "The Rattrap", "content": "A philosophical tale about a peddler who views the world as a giant rattrap."},
                    {"number": "5", "title": "Indigo", "content": "Louis Fischer details Mahatma Gandhi's struggle for the Champaran sharecroppers."}
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
