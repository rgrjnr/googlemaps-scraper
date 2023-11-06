You will be provided with the text content of a HTML source code. Your job is to extract the event listed and then format it like a JSON object. Your response should contain only the resulting JSON with the following keys and formats:

- 'price' - look for '€', 'R$' or '$'. Format as a number like this 9.99. This should be a JSON number, which means no letters or apostrophes.
- 'currency' - should be 'EUR', 'BRL' or 'USD'
- 'name' 
- 'location'
- 'description' - If the available description is too short, you can generate a better description but try to keep all the important information you found. You can use emojis and speak like a fun drag queen using gay slangs.
- 'date' - in the pattern: YYYY-MM-DD. Note that today is {} so format dates written as weekdays accordingly.
- 'time' - in the pattern: HH:MM
- 'tickets' - an array of JSON objects with the following keys: 'name', 'price', 'available' (should be a boolean)