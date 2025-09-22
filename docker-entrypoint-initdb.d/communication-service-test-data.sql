-- This script will populate the Messages table with initial data, if it's empty.
-- If any error occurs, the EXCEPTION block will handle it, and the transaction will be rolled back.

BEGIN;

DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM "Messages") THEN
            INSERT INTO "Messages" ("Id", "LobbyId", "ChannelName", "SenderId", "SenderName", "Content", "Timestamp")
            VALUES
                (gen_random_uuid(), 'seed_lobby_1', NULL, 101, 'Alice', 'Hey everyone! Welcome to the game.', NOW() - INTERVAL '10 minutes'),
                (gen_random_uuid(), 'seed_lobby_1', NULL, 102, 'Bob', 'Hi Alice! Glad to be here.', NOW() - INTERVAL '9 minutes'),
                (gen_random_uuid(), 'seed_lobby_1', 'mafia', 103, 'Godfather', 'Alright team, let''s get organized.', NOW() - INTERVAL '8 minutes'),
                (gen_random_uuid(), 'seed_lobby_1', 'mafia', 104, 'Consigliere', 'I have a plan. We should target the doctor first.', NOW() - INTERVAL '7 minutes'),
                (gen_random_uuid(), 'seed_lobby_1', 'detectives', 105, 'Sherlock', 'I''m getting a strange vibe from Bob.', NOW() - INTERVAL '6 minutes'),
                (gen_random_uuid(), 'seed_lobby_1', 'detectives', 106, 'Watson', 'Agreed. Let''s keep an eye on him.', NOW() - INTERVAL '5 minutes'),

                (gen_random_uuid(), 'seed_lobby_2', NULL, 201, 'Charlie', 'Is this lobby active?', NOW() - INTERVAL '15 minutes'),
                (gen_random_uuid(), 'seed_lobby_2', NULL, 202, 'Diana', 'Yes! We''re just waiting for a few more players to join.', NOW() - INTERVAL '14 minutes'),
                (gen_random_uuid(), 'seed_lobby_2', 'mafia', 203, 'Don', 'Let''s make this quick. No mistakes tonight.', NOW() - INTERVAL '12 minutes'),
                (gen_random_uuid(), 'seed_lobby_2', 'mafia', 204, 'Capo', 'Understood, Don. I have my target.', NOW() - INTERVAL '11 minutes'),
                (gen_random_uuid(), 'seed_lobby_2', 'detectives', 205, 'Inspector', 'I''ve got a lead on one of the suspects.', NOW() - INTERVAL '10 minutes'),
                (gen_random_uuid(), 'seed_lobby_2', 'detectives', 206, 'Sleuth', 'Let''s gather more evidence before we make a move.', NOW() - INTERVAL '9 minutes');

            RAISE NOTICE 'Database seeded with initial data.';
        ELSE
            RAISE NOTICE 'Database already contains data. Seeding skipped.';
        END IF;

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'An error occurred: %', SQLERRM;
            RAISE NOTICE 'Transaction is being rolled back.';
            RAISE;
    END;
$$;

COMMIT;