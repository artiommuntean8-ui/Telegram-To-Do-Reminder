# To-Do Reminder Telegram Bot

A simple yet effective Telegram bot to help you manage your to-do list and get reminders for your tasks.

## Features

-   Add tasks with a specific reminder time (supports full date or just time for today).
-   List all your active tasks.
-   Mark tasks as completed via command or interactive button.
-   Delete tasks.
-   Clear all completed tasks at once.
-   Get timely reminders for your tasks.
-   Persistent reminders: Even if the bot restarts, your reminders are safe.

## Commands

-   `/start` - Displays a welcome message and lists all available commands.
-   `/add <Task Text> | <Time>` - Adds a new task. Example: `/add Buy Milk | 18:00` or `/add Report | 2024-12-31 23:59`.
-   `/list` - Shows a list of your active (pending) tasks with their IDs.
-   `/done <ID>` - Marks a task as completed. The reminder for this task will be cancelled.
-   `/delete <ID>` - Deletes a task and its corresponding reminder.
-   `/clear` - Deletes all completed tasks from the database.

## Setup and Installation

Follow these steps to get the bot running on your own machine.

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    The project dependencies are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your Bot Token:**
    -   Get a bot token from BotFather on Telegram.
    -   Create a file named `.env` in the project's root directory.
    -   Add your token to the `.env` file like this:
        ```
        BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        ```

5.  **Run the bot:**
    ```bash
    python todo_bot.py
    ```

Your bot should now be running and responsive on Telegram!