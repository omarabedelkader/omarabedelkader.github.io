function myFunction() {
    var x = document.getElementById("myDIV");
    if (x.style.display === "none") {
      x.style.display = "block";
      document.getElementById("myButton1").innerHTML="<a href='mailto:omarabedelkader1@gmail.com?'>omarabedelkader1@gmail.com</a>";
    } else {
      x.style.display = "none";
      document.getElementById("myButton1").innerHTML="<a href='mailto:omarabedelkader1@gmail.com?'>omarabedelkader1@gmail.com</a>";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("year").textContent = new Date().getFullYear();
  });


