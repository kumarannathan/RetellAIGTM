export const handler = async (event) => {
    // Only allow POST
    if (event.httpMethod !== "POST") {
        return { statusCode: 405, body: "Method Not Allowed" };
    }

    try {
        const data = JSON.parse(event.body || "{}");
        const query = data.query || "software engineer new grad";

        const url = `https://jsearch.p.rapidapi.com/search?query=${encodeURIComponent(query)}&page=1&num_pages=1`;
        const response = await fetch(url, {
            headers: {
                "x-rapidapi-host": "jsearch.p.rapidapi.com",
                // Store your real key in Netlify Environment Variables
                "x-rapidapi-key": process.env.JSEARCH_API_KEY || "658204ac81msh00f29a23afa6fc3p18f576jsn088e26849052"
            }
        });
        
        const responseData = await response.json();
        
        return {
            statusCode: 200,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" // CORS
            },
            body: JSON.stringify(responseData)
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};
