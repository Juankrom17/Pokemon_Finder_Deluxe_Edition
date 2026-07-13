# Pokémon Finder

<table width="100%">
  <tr>
    <td width="50%" valign="top">
      <h3>System Requirements</h3>
      <p>To ensure proper screen scanning and system library management, this program requires Administrator privileges to run. The software will automatically request these permissions upon startup.</p>
      <ul>
        <li><b>Tesseract OCR:</b> The program automatically checks for its presence on the computer. If it is not found, it provides an option to download and install it in an automated manner.</li>
        </li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>Project Description</h3>
      <p>Pokémon Finder Deluxe is an application designed to scan specific areas of the screen while playing on emulators or native PC titles. Its main function is to extract text from dialogue boxes, automatically identify Pokémon names using natural language processing, and open detailed information for each species directly in your default web browser.</p>
      <p>The system features a multi-contrast image processing engine and connects to updated databases, allowing it to adapt to different fonts, resolutions, and game interfaces.</p>
    </td>
  </tr>
</table>

---

## Instructions for Use

### 1. Configuring Reading Zones
Before capturing any text, you need to define which areas of the screen the program should analyze:
* Start your game and make sure the window is visible.
* Press the F8 key or click the button to add a new dialogue box in the main menu.
* The screen will dim slightly. Click and drag the cursor to draw a rectangle over the section where the game texts or dialogues appear.
* Upon releasing the click, the program will prompt you to press a key (for example: Q, 1, or F4) to associate it with that specific zone.

### 2. Capture and Information Retrieval
* Once the zones are configured, you can minimize the application interface and play normally.
* When a text containing a Pokémon's name appears in the game, press the key you assigned in the previous step.
* The program will take an internal capture of that sector, process the text invisibly, and open the corresponding tab in Pokémon Database.
* The main interface features a preview box that allows you to verify the last capture taken.

### 3. Correction and Learning System
The reading system is designed to mitigate errors caused by complex typography, pixelated fonts, or backgrounds with visual noise:
* **Resolving Ambiguities:** If the reading engine detects more than one potential name in the same text, it will display a pop-up window so the user can select the correct option. The program will remember this decision for future analyses.
* **Associating Erroneous Texts:** If the scan returns corrupted characters or an incorrect name, you can use the option to correct the last capture. By entering the actual name, the software will permanently link that faulty reading to the correct Pokémon.
* **Memory Management:** The option to manage learned decisions allows you to review, modify, or delete the history of accumulated corrections.

---

## Technical Features

* **Background Detection:** The program responds to the configured capture keys even if the game is in full screen or if the application window is minimized.
* **Automated Updates:** Upon startup, the program checks if there is a newer version available on GitHub. If a new executable is found, it offers the option to download and replace the previous one automatically, preserving user configurations.
* **Data Persistence:** Zone coordinates and text corrections are stored locally in JSON format files, ensuring that the information remains available at every launch.
* **Adaptive Network Mode:** The software attempts to connect to the official Pokémon API to keep its database up to date. If it does not detect an active internet connection, it automatically switches to a local mode to operate offline.

---
Developed by Juan Esteban Kromberger and Gino Laprovida.
