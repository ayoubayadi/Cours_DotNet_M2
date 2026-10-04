using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using WebApplicationEmploye.Models;
using WebApplicationEmploye.Models.Repositories;
namespace WebApplicationEmploye.Controllers
{
    public class EmployeeController : Controller
    {
        private readonly IRepository<Employee> EmployeeRepository;
        // Injection de dépendance
        public EmployeeController(IRepository<Employee> empRepository)
        {
            EmployeeRepository = empRepository;
        }

        // GET: Employee
        public ActionResult Index()
        {
            var employees = EmployeeRepository.GetAll();

            ViewData["EmployeesCount"] = employees.Count();
            ViewData["SalaryAverage"] = EmployeeRepository.SalaryAverage();
            ViewData["MaxSalary"] = EmployeeRepository.MaxSalary();
            ViewData["HREmployeesCount"] = EmployeeRepository.HrEmployeesCount();

            return View(employees);
        }

        // Search
        public ActionResult Search(string term)
        {
            var result = EmployeeRepository.Search(term);
            return View("Index", result);
        }

        // GET: EmployeeController/Details/5
        public ActionResult Details(int id)
        {
            var employee = EmployeeRepository.FindByID(id);
            return View(employee);
        }

        // GET: EmployeeController/Create
        public ActionResult Create()
        {
            return View();
        }

        // POST: EmployeeController/Create
        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Create(Employee emp)
        {
            try
            {
                EmployeeRepository.Add(emp);
                return RedirectToAction(nameof(Index));
            }
            catch
            {
                return View();
            }
        }

        // GET: EmployeeController/Edit/5
        public ActionResult Edit(int id)
        {
            return View();
        }

        // POST: EmployeeController/Edit/5
        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Edit(int id, Employee newEmployee)
        {
            try
            {
                EmployeeRepository.Update(id, newEmployee);
                return RedirectToAction(nameof(Index));
            }
            catch
            {
                return View();
            }
        }

        // GET: EmployeeController/Delete/5
        public ActionResult Delete(int id)
        {
            return View();
        }

        // POST: EmployeeController/Delete/5
        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Delete(int id, Employee employee)
        {
            try
            {
                EmployeeRepository.Delete(id);
                return RedirectToAction(nameof(Index));
            }
            catch
            {
                return View();
            }
        }
    }
}
