const form = document.getElementById("loginForm");
const username = document.getElementById("username");
const password = document.getElementById("password");
const toggle = document.getElementById("togglePassword");
const errorBox = document.getElementById("error");

// Show / hide password
toggle.addEventListener("click", () => {
    const show = password.type === "password";

    password.type = show ? "text" : "password";

    toggle.classList.toggle("on", show);

    toggle.setAttribute(
        "aria-label",
        show ? "Hide password" : "Show password"
    );
});


// Login submit
form.addEventListener("submit", async (e) => {

    e.preventDefault();

    errorBox.textContent = "";

    const user = username.value.trim();
    const pass = password.value;
    const role = form.elements["role"].value;

    if (!user || !pass) {
        errorBox.textContent =
            "Please enter your username and password.";
        return;
    }

    try {

        const response = await fetch(
            "http://127.0.0.1:5000/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    username: user,
                    password: pass
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            errorBox.textContent =
                data.error || "Login failed.";
            return;
        }

       // Check user role from database
const roleMatches = role === "student"
    ? ["student", "staff"].includes(data.user.role)
    : data.user.role === role;

if (!roleMatches) {

    errorBox.textContent =
        "Selected user type does not match your account.";

    return;
}

        // Save logged-in user details
        localStorage.setItem(
            "loggedInUser",
            JSON.stringify(data.user)
        );

        // Redirect according to user role
        const pages = {
            student: "student-dashboard.html",
            staff: "student-dashboard.html",
            doctor: "doctor-dashboard.html",
            admin: "admin-dashboard.html"
        };

        window.location.href = pages[data.user.role];

    } catch (error) {

        console.error("Login Error:", error);

        errorBox.textContent =
            "Cannot connect to the server. Please try again.";

    }

});