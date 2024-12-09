document.addEventListener("DOMContentLoaded", () => {
  let pieceCount = 1; // Start from 1 since we already have one piece by default

  const addPieceButton = document.getElementById("add_piece_button");
  const numPiecesInput = document.getElementById("num_pieces");
  const piecesContainer = document.getElementById("pieces_container");

  if (addPieceButton) {
    addPieceButton.addEventListener("click", () => {
      pieceCount++;
      if (numPiecesInput) {
        numPiecesInput.value = pieceCount.toString();
      }

      if (piecesContainer) {
        const pieceHTML = `
          <h4>Piece ${pieceCount}</h4>
          <label>pieceNum:</label> <input type="text" name="pieceNum_${pieceCount}"><br>
          <label>pDescription:</label><input type="text" name="pDescription_${pieceCount}"><br>
          <label>length:</label><input type="text" name="length_${pieceCount}"><br>
          <label>width:</label><input type="text" name="width_${pieceCount}"><br>
          <label>height:</label><input type="text" name="height_${pieceCount}"><br>
          <label>roomNum:</label><input type="text" name="roomNum_${pieceCount}"><br>
          <label>shelfNum:</label><input type="text" name="shelfNum_${pieceCount}"><br>
          <label>pNotes:</label><input type="text" name="pNotes_${pieceCount}"><br><br>
        `;
        piecesContainer.insertAdjacentHTML("beforeend", pieceHTML);
      }
    });
  }
});
