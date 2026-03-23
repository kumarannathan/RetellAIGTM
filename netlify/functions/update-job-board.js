export const handler = async (event) => {
    // Only allow POST
    if (event.httpMethod !== "POST") {
        return { statusCode: 405, body: "Method Not Allowed" };
    }

    try {
        const payload = JSON.parse(event.body || "{}");
        // Your logic to check required fields in payload (like title, company)
        if (!payload.title || !payload.company) {
            return { statusCode: 400, body: JSON.stringify({ error: "Missing title or company" }) };
        }

        // Configuration required for GitHub API
        // Add these to your Netlify Environment Variables
        const GITHUB_TOKEN = process.env.GITHUB_PAT;
        const GITHUB_OWNER = process.env.GITHUB_OWNER || "kumarannathan"; 
        const GITHUB_REPO = process.env.GITHUB_REPO || "RetellAIGTM"; 
        
        if (!GITHUB_TOKEN) {
            return { statusCode: 500, body: JSON.stringify({ error: "GitHub PAT not configured" }) };
        }

        const filePath = "jobs.json";
        const apiUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${filePath}`;
        
        // 1. Get the current jobs.json from GitHub to get its SHA and current content
        const getFileRes = await fetch(apiUrl, {
            headers: {
                "Authorization": `Bearer ${GITHUB_TOKEN}`,
                "Accept": "application/vnd.github.v3+json"
            }
        });

        if (!getFileRes.ok) {
            return { statusCode: 500, body: JSON.stringify({ error: "Failed to fetch from GitHub" }) };
        }

        const fileData = await getFileRes.json();
        const sha = fileData.sha;
        
        // Decode base64 content
        const currentContentStr = Buffer.from(fileData.content, 'base64').toString('utf8');
        const currentJobs = JSON.parse(currentContentStr);

        // 2. Add the new job to the top
        const newJob = {
            id: String(Date.now()),
            title: payload.title,
            date: payload.date || new Date().toISOString().split('T')[0],
            salary: payload.salary || "",
            company: payload.company,
            link: payload.link || ""
        };
        currentJobs.unshift(newJob);

        // 3. Commit the updated jobs.json back to GitHub
        const newContentBase64 = Buffer.from(JSON.stringify(currentJobs, null, 2)).toString('base64');
        const updateParams = {
            message: `Add new job: ${newJob.title} at ${newJob.company} (via Clawdbot)`,
            content: newContentBase64,
            sha: sha,
            branch: "main" // Change if your default branch is different
        };

        const updateRes = await fetch(apiUrl, {
            method: "PUT",
            headers: {
                "Authorization": `Bearer ${GITHUB_TOKEN}`,
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(updateParams)
        });

        if (!updateRes.ok) {
            // Read error text for debugging
            const errorText = await updateRes.text();
            throw new Error(`GitHub API error: ${errorText}`);
        }

        // Committing to the repo will automatically trigger a Netlify build

        return {
            statusCode: 202,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: "Job added and pushed to GitHub successfully", job: newJob })
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};
