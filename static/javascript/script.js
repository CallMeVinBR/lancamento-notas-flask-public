function opcao_aluno(){
    var conta_aluno = document.getElementById("opcao-aluno");
    var conta_prof = document.getElementById("opcao-prof");
  
    conta_prof.style.backgroundColor = "white";
    conta_prof.style.borderRadius = 0;
    conta_prof.style.color = "green";
  
    conta_aluno.style.backgroundColor = "#26A31B";
    conta_aluno.style.borderRadius = "10px";
    conta_aluno.style.color = "white";
  
    event.preventDefault();
}
  
function opcao_prof(){
    var conta_aluno = document.getElementById("opcao-aluno");
    var conta_prof = document.getElementById("opcao-prof");
  
    conta_aluno.style.backgroundColor = "white";
    conta_aluno.style.borderRadius = 0;
    conta_aluno.style.color = "green";
  
    conta_prof.style.backgroundColor = "#26A31B";
    conta_prof.style.borderRadius = "10px";
    conta_prof.style.color = "white";
  
    event.preventDefault();
}